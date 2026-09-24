import http.client
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
import io
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/codex-history/scripts"
sys.path.insert(0, str(SCRIPTS))
from history_reader import HistoryStore, HistoryError, read_rollout, entry
from history import DemoStore, make_handler, ThreadingHTTPServer, open_snapshot
from standalone import build_html


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def test_sqlite_keeps_repeated_questions_phases_and_order_without_mutation(self):
        path = self.home / 'thread_history_1.sqlite'
        with sqlite3.connect(path) as c:
            c.execute('CREATE TABLE thread_items(thread_id TEXT,item_json TEXT,created_at_ms INTEGER,rollout_ordinal INTEGER)')
            items = [
                {'type':'userMessage','content':[{'type':'text','text':'相同的问题？'}]},
                {'type':'agentMessage','text':'Checking…','phase':'commentary'},
                {'type':'reasoning','summary':['Saved summary'],'content':['Raw payload must not be shown']},
                {'type':'agentMessage','text':'First answer','phase':'final_answer'},
                {'type':'userMessage','content':[{'type':'text','text':'相同的问题？'}]},
                {'type':'agentMessage','text':'Second answer','phase':'final_answer'},
            ]
            for i, item in enumerate(items): c.execute('INSERT INTO thread_items VALUES(?,?,?,?)', ('selected',json.dumps(item),i,i))
            c.execute('INSERT INTO thread_items VALUES(?,?,?,?)', ('other',json.dumps({'type':'userMessage','content':[{'text':'OTHER PRIVATE CONVERSATION'}]}),0,0))
        before = path.read_bytes()
        result = HistoryStore('selected', home=self.home).read()
        self.assertEqual([q['text'] for q in result['questions']], ['相同的问题？','相同的问题？'])
        self.assertEqual([m['text'] for m in result['messages']], ['相同的问题？','Checking…','Saved summary','First answer','相同的问题？','Second answer'])
        self.assertEqual(result['messages'][1]['phase'], 'commentary')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(result['revision'], HistoryStore('selected', home=self.home).read()['revision'])

    def test_legacy_deduplicates_event_and_response_but_keeps_two_identical_turns(self):
        path = self.home / 'rollout.jsonl'
        records = []
        for _ in range(2):
            records.extend([
                {'type':'response_item','payload':{'type':'message','role':'user','content':[{'text':'Again'}]}},
                {'type':'event_msg','payload':{'type':'user_message','message':'Again'}},
                {'type':'response_item','payload':{'type':'function_call','name':'shell','call_id':'c','arguments':'{"cmd":"pwd"}'}},
                {'type':'response_item','payload':{'type':'function_call_output','call_id':'c','output':'/workspace'}},
                {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer','content':[{'text':'Answer'}]}},
                {'type':'event_msg','payload':{'type':'agent_message','message':'Answer'}},
            ])
        path.write_text('\n'.join(json.dumps(r) for r in records)+'\n{"unfinished"', encoding='utf-8')
        result = HistoryStore(rollout=path).read()
        self.assertEqual([m['kind'] for m in result['messages']], ['user','tool','assistant'] * 2)
        self.assertEqual(len(result['questions']), 2)
        self.assertTrue(result['messages'][1]['text'].endswith('/workspace'))
        self.assertEqual(len(result['warnings']), 1)

    def test_no_current_id_never_guesses_another_session(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HistoryError): HistoryStore(home=self.home)

    def test_desktop_clarification_reply_shows_human_answer_and_question(self):
        text = '<send_user_message_question_reply>' + json.dumps([{'questionItemId':'internal-id','question':'Which view?','answer':'A readable browser page.'}]) + '</send_user_message_question_reply>'
        self.assertEqual(entry('user', text)['text'], 'A readable browser page.\n\n> Which view?')
        malformed = '<send_user_message_question_reply>not-json</send_user_message_question_reply>'
        self.assertEqual(entry('user', malformed)['text'], malformed)

    def test_literal_id_cannot_expand_glob(self):
        session = self.home / 'sessions/2026/01/01'
        session.mkdir(parents=True)
        (session/'rollout-private.jsonl').write_text('{}')
        with self.assertRaises(HistoryError): HistoryStore('*',home=self.home).read()

    def test_fallback_finds_archived_rollout(self):
        directory = self.home / 'archived_sessions'; directory.mkdir()
        file = directory / 'rollout-2026-01-01-selected.jsonl'
        file.write_text(json.dumps({'type':'event_msg','payload':{'type':'user_message','message':'Archived'}}))
        self.assertEqual(HistoryStore('selected',home=self.home).read()['questions'][0]['text'],'Archived')

    def test_legacy_fallback_excludes_setup_and_preserves_code_and_math(self):
        path = self.home / 'legacy.jsonl'
        prompt = 'Question $x$\n```python\nprint("hi")\n```'
        rows = [
            {'type':'response_item','payload':{'type':'message','role':'user','content':[{'text':'<environment_context>setup</environment_context>'}]}},
            {'type':'response_item','payload':{'type':'message','role':'user','content':[{'text':prompt}]}},
            {'type':'event_msg','payload':{'type':'agent_message','message':'Final answer'}},
        ]
        path.write_text('\n'.join(map(json.dumps, rows)))
        result = HistoryStore(rollout=path).read()
        self.assertEqual([m['text'] for m in result['messages']], [prompt, 'Final answer'])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1',0),make_handler(DemoStore(),'secret-test-token'))
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self,path,headers=None):
        c = http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        c.request('GET',path,headers=headers or {})
        response = c.getresponse(); result = response.status,dict(response.getheaders()),response.read(); c.close()
        return result

    def test_history_is_private_and_readable_with_capability(self):
        self.assertEqual(self.request('/api/history')[0],403)
        self.assertEqual(self.request('/api/history?token=wrong')[0],403)
        status,headers,body = self.request('/api/history?token=secret-test-token')
        self.assertEqual(status,200)
        self.assertEqual(len(json.loads(body)['questions']),4)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertNotIn('Access-Control-Allow-Origin',headers)

    def test_rejects_cross_origin_host_rebinding_and_path_escape(self):
        path = '/api/history?token=secret-test-token'
        self.assertEqual(self.request(path,{'Host':'attacker.example'})[0],403)
        self.assertEqual(self.request(path,{'Origin':'https://attacker.example'})[0],403)
        self.assertEqual(self.request('/vendor/../../scripts/history.py')[0],404)
        self.assertEqual(self.request('/vendor/marked.js')[0],200)
        self.assertEqual(self.request('/vendor/fonts/KaTeX_Main-Regular.woff2')[0],200)

    def test_html_only_loads_bundled_assets(self):
        status,headers,body = self.request('/?token=secret-test-token')
        self.assertEqual(status,200)
        self.assertNotIn(b'__TOKEN__',body)
        self.assertIn(b'/vendor/katex.js?token=secret-test-token',body)
        self.assertIn("connect-src 'self'",headers['Content-Security-Policy'])


class ExportTests(unittest.TestCase):
    def test_default_snapshot_requests_browser_without_binding_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch('history.tempfile.mkdtemp', return_value=directory), patch('history.webbrowser.open', return_value=True) as browser, patch('history.ThreadingHTTPServer', side_effect=AssertionError('Must not bind a port')):
                with redirect_stdout(output):
                    open_snapshot(Namespace(demo=True, no_open=False))
            result = json.loads(output.getvalue())
            self.assertEqual(result['mode'], 'offline')
            self.assertTrue(result['browserOpened'])
            self.assertTrue(Path(result['path']).is_file())
            browser.assert_called_once_with(Path(result['path']).as_uri())

    def test_browser_denied_preserves_snapshot_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch('history.tempfile.mkdtemp', return_value=directory), patch('history.webbrowser.open', side_effect=PermissionError('Operation not permitted')):
                with redirect_stdout(output):
                    open_snapshot(Namespace(demo=True, no_open=False))
            result = json.loads(output.getvalue())
            self.assertFalse(result['browserOpened'])
            self.assertIn('Operation not permitted', result['browserOpenError'])
            self.assertTrue(Path(result['path']).is_file())

    def test_standalone_embeds_assets_and_escapes_script_breakout(self):
        data = DemoStore().read()
        data['messages'][0]['text'] = '</script><script>alert("injected")</script>'
        html = build_html(data)
        self.assertNotIn('src="/vendor/',html)
        self.assertNotIn('href="/viewer.css',html)
        self.assertNotIn('url(fonts/',html)
        self.assertIn('data:font/woff2;base64,',html)
        self.assertNotIn('</script><script>alert("injected")',html)
        self.assertIn('\\u003c/script>',html)


if __name__ == '__main__': unittest.main()
