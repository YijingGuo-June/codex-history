'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const token = new URL(location.href).searchParams.get('token') || '';
  const embedded = document.getElementById('history-data');
  const state = {data: null, pending: null, selected: 0, matches: [], clean: true, active: 1};
  const escape = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const storage = {get(key) {try {return localStorage.getItem(key);} catch {return null;}}, set(key, value) {try {localStorage.setItem(key, value);} catch {}}};
  const theme = storage.get('codex-history-theme');
  if (theme === 'dark') document.body.classList.add('dark');
  state.clean = storage.get('codex-history-clean') !== 'false';
  $('toggle-details').setAttribute('aria-pressed', String(state.clean));

  function math(text, displayMode) {
    try {return katex.renderToString(text, {displayMode, throwOnError: false, trust: false, strict: 'ignore', maxExpand: 1000, maxSize: 20});}
    catch {return '<code class="math-error">' + escape(text) + '</code>';}
  }
  marked.use({gfm: true, breaks: false, renderer: {
    html({text}) {return escape(text);},
    image({text}) {return '<span class="attachment">[Image: ' + escape(text || 'attachment') + ']</span>';},
  }, extensions: [{
    name: 'displayMath', level: 'block',
    start(src) {return src.match(/\$\$|\\\[/)?.index;},
    tokenizer(src) {
      const match = /^(?: {0,3})(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])(?:[ \t]*(?:\n|$))/.exec(src);
      if (match) return {type: 'displayMath', raw: match[0], text: match[1] ?? match[2]};
    }, renderer(item) {return math(item.text, true);},
  }, {
    name: 'inlineMath', level: 'inline',
    start(src) {return src.match(/\$|\\\(/)?.index;},
    tokenizer(src) {
      const match = /^(?:\\\(([\s\S]+?)\\\)|\$(?![\s$])((?:\\.|[^$\\\n])+?)\$(?!\d))/.exec(src);
      if (match) return {type: 'inlineMath', raw: match[0], text: match[1] ?? match[2]};
    }, renderer(item) {return math(item.text, false);},
  }]});

  function markdown(text) {
    const container = document.createElement('div');
    container.className = 'markdown';
    try {
      container.append(DOMPurify.sanitize(marked.parse(text || ''), {
        RETURN_DOM_FRAGMENT: true, SANITIZE_NAMED_PROPS: true,
        FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'textarea', 'select', 'img', 'image', 'use'],
      }));
    } catch {
      container.textContent = text;
      container.style.whiteSpace = 'pre-wrap';
    }
    container.querySelectorAll('a').forEach(link => {
      if (!/^(https?:|mailto:)/i.test(link.getAttribute('href') || '')) link.removeAttribute('href');
      else {link.target = '_blank'; link.rel = 'noreferrer noopener';}
    });
    container.querySelectorAll('table').forEach(table => {
      const wrap = document.createElement('div'); wrap.className = 'table-wrap';
      table.before(wrap); wrap.append(table);
    });
    container.querySelectorAll('pre > code').forEach(code => {
      const language = code.className.match(/language-([\w-]+)/)?.[1] || 'text';
      const aliases = {py:'python', sh:'bash', shell:'bash', js:'javascript', ts:'typescript', rs:'rust'};
      const grammar = Prism.languages[aliases[language] || language];
      const original = code.textContent;
      if (grammar && original.length < 100000) code.innerHTML = Prism.highlight(original, grammar, language);
      const header = document.createElement('div'); header.className = 'code-header';
      const label = document.createElement('span'); label.textContent = language;
      const copy = document.createElement('button'); copy.className = 'copy-button'; copy.textContent = 'Copy';
      copy.setAttribute('aria-label', 'Copy code');
      copy.addEventListener('click', async () => {
        try {await navigator.clipboard.writeText(original); copy.textContent = 'Copied';}
        catch {copy.textContent = 'Select to copy';}
        setTimeout(() => {copy.textContent = 'Copy';}, 1600);
      });
      header.append(label, copy); code.parentElement.prepend(header);
    });
    return container;
  }

  function label(role, detail, symbol) {
    const row = document.createElement('div'); row.className = 'message-label';
    const icon = document.createElement('span'); icon.className = 'role-icon'; icon.textContent = symbol;
    const name = document.createElement('span'); name.textContent = role;
    const meta = document.createElement('span'); meta.className = 'message-kind'; meta.textContent = detail;
    row.append(icon, name, meta); return row;
  }
  const isAnswer = message => message.kind === 'assistant' && message.phase !== 'commentary';
  function renderMessage(message) {
    const node = document.createElement('article'); node.id = message.id; node.className = 'message';
    if (message.kind === 'user') {
      node.classList.add('user'); node.dataset.question = message.question;
      node.append(label('YOU', 'QUESTION ' + String(message.question).padStart(2, '0'), '↗'), markdown(message.text));
    } else if (isAnswer(message)) {
      node.classList.add('assistant'); node.append(label('CODEX', 'FINAL ANSWER', '✳'), markdown(message.text));
    } else {
      node.classList.add('activity'); node.hidden = state.clean;
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      const names = {reasoning: 'Reasoning summary', tool: 'Tool activity', status: 'Session event', assistant: 'Progress update'};
      summary.textContent = names[message.kind] || 'Activity';
      const preview = document.createElement('span'); preview.textContent = (message.text || '').split('\n')[0].slice(0, 75);
      summary.append(preview); details.append(summary);
      details.addEventListener('toggle', () => {
        if (!details.open || details.childElementCount > 1) return;
        if (message.kind === 'tool') {const pre = document.createElement('pre'); pre.className = 'raw-output'; pre.textContent = message.text; details.append(pre);}
        else details.append(markdown(message.text || 'No saved summary available.'));
      });
      node.append(details);
    }
    return node;
  }

  function readingAnchor() {
    const top = $('reader').getBoundingClientRect().top;
    const candidates = [...document.querySelectorAll('.message:not([hidden])')];
    const item = candidates.find(node => node.getBoundingClientRect().bottom > top + 20);
    return item ? {id: item.id, offset: item.getBoundingClientRect().top - top} : null;
  }
  function restoreAnchor(anchor) {
    const target = anchor && $(anchor.id);
    if (target && !target.hidden) $('reader').scrollTop += target.getBoundingClientRect().top - $('reader').getBoundingClientRect().top - anchor.offset;
  }
  function render(data) {
    const anchor = readingAnchor();
    const openDetails = new Set([...document.querySelectorAll('details[open]')].map(node => node.parentElement.id));
    state.data = data;
    $('session-label').textContent = data.threadId === 'demo-conversation' ? 'Demo conversation' : data.threadId.slice(0, 8);
    $('source-label').textContent = data.source === 'Demo' ? 'SAMPLE CONVERSATION' : 'LOCAL ARCHIVE';
    $('question-count').textContent = data.questions.length;
    $('document-count').textContent = `${data.questions.length} questions · ${data.messages.filter(isAnswer).length} answers`;
    const nav = document.createDocumentFragment();
    data.questions.forEach(question => {
      const button = document.createElement('button'); button.className = 'question-link'; button.dataset.number = question.number;
      const number = document.createElement('span'); number.className = 'number'; number.textContent = String(question.number).padStart(2, '0');
      const preview = document.createElement('span'); preview.className = 'question-preview'; preview.textContent = question.text || '[Attachment]';
      button.append(number, preview); button.addEventListener('click', () => jump(question)); nav.append(button);
    });
    $('questions').replaceChildren(nav);
    const fragment = document.createDocumentFragment();
    data.messages.forEach(message => fragment.append(renderMessage(message)));
    $('messages').replaceChildren(fragment);
    openDetails.forEach(id => {const details = $(id)?.querySelector('details'); if (details) details.open = true;});
    $('empty').hidden = data.questions.length > 0;
    data.questions.forEach((question, i) => {
      const start = data.messages.findIndex(message => message.id === question.messageId);
      const end = i + 1 < data.questions.length ? data.messages.findIndex(message => message.id === data.questions[i + 1].messageId) : data.messages.length;
      if (!data.messages.slice(start + 1, end).some(isAnswer)) {
        const pending = document.createElement('p'); pending.className = 'pending'; pending.textContent = 'No final answer saved yet.';
        $(question.messageId).append(pending);
      }
    });
    restoreAnchor(anchor); updateActive();
    if (data.warnings.length) notice(data.warnings.join(' '));
  }

  function jump(question) {
    if ($('picker').open) $('picker').close();
    const target = $(question.messageId);
    if (!target) return;
    target.scrollIntoView({block: 'start', behavior: 'instant'});
    target.classList.remove('jump-flash'); void target.offsetWidth; target.classList.add('jump-flash');
    state.active = question.number; updateActive(); $('reader').focus({preventScroll: true});
  }
  function updateActive() {
    const top = $('reader').getBoundingClientRect().top + 90;
    let active = state.data?.questions[0]?.number;
    document.querySelectorAll('.message.user').forEach(node => {if (node.getBoundingClientRect().top <= top) active = Number(node.dataset.question);});
    state.active = active;
    document.querySelectorAll('.question-link').forEach(button => {
      const current = Number(button.dataset.number) === active;
      button.classList.toggle('active', current);
      if (current) button.setAttribute('aria-current', 'location'); else button.removeAttribute('aria-current');
    });
  }
  let scrollFrame = null;
  $('reader').addEventListener('scroll', () => {
    if (scrollFrame !== null) return;
    scrollFrame = requestAnimationFrame(() => {updateActive(); scrollFrame = null;});
  }, {passive: true});

  function search() {
    const needle = $('query').value.trim().toLocaleLowerCase();
    state.matches = (state.data?.questions || []).filter(q => q.text.toLocaleLowerCase().includes(needle));
    state.selected = 0; drawResults();
  }
  function drawResults() {
    $('matches').textContent = `${state.matches.length} FOUND`;
    const fragment = document.createDocumentFragment();
    state.matches.forEach((question, index) => {
      const button = document.createElement('button'); button.className = 'result'; button.id = 'result-' + index; button.setAttribute('role', 'option'); button.setAttribute('aria-selected', String(index === state.selected)); button.tabIndex = -1;
      const number = document.createElement('span'); number.className = 'result-number'; number.textContent = String(question.number).padStart(2, '0');
      const text = document.createElement('div'); text.className = 'result-text';
      const preview = document.createElement('span'); preview.textContent = question.text || '[Attachment]'; text.append(preview);
      const enter = document.createElement('span'); enter.className = 'result-enter'; enter.textContent = '↵';
      button.append(number, text, enter); button.addEventListener('click', () => jump(question)); fragment.append(button);
    });
    if (!state.matches.length) {const empty = document.createElement('div'); empty.className = 'no-results'; empty.textContent = 'No matching questions. Try a different phrase.'; fragment.append(empty);}
    $('results').replaceChildren(fragment);
    if (state.matches.length) $('query').setAttribute('aria-activedescendant', 'result-' + state.selected); else $('query').removeAttribute('aria-activedescendant');
  }
  function openPicker() {
    $('query').value = ''; search();
    state.selected = Math.max(0, state.matches.findIndex(q => q.number === state.active)); drawResults();
    $('picker').showModal(); $('query').focus();
    $('result-' + state.selected)?.scrollIntoView({block: 'nearest'});
  }
  $('query').setAttribute('role', 'combobox'); $('query').setAttribute('aria-controls', 'results'); $('query').setAttribute('aria-autocomplete', 'list');
  $('query').addEventListener('input', search);
  $('query').addEventListener('keydown', event => {
    if (event.isComposing) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); state.selected = Math.max(0, Math.min(state.matches.length - 1, state.selected + (event.key === 'ArrowDown' ? 1 : -1))); drawResults();
      $('result-' + state.selected)?.scrollIntoView({block: 'nearest'});
    } else if (event.key === 'Enter' && state.matches[state.selected]) {event.preventDefault(); jump(state.matches[state.selected]);}
  });
  $('open-picker').addEventListener('click', openPicker);
  $('close-picker').addEventListener('click', () => $('picker').close());
  $('picker').addEventListener('click', event => {if (event.target === $('picker')) {const r = $('picker').getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('picker').close();}});

  function toggleDetails() {
    const anchor = readingAnchor(); state.clean = !state.clean;
    storage.set('codex-history-clean', String(state.clean));
    $('toggle-details').setAttribute('aria-pressed', String(state.clean));
    document.querySelectorAll('.message.activity').forEach(node => {node.hidden = state.clean;});
    if (anchor && $(anchor.id)?.hidden) {
      const question = state.data.questions.find(q => q.number === state.active);
      if (question) jump(question);
    } else restoreAnchor(anchor);
    updateActive();
  }
  $('toggle-details').addEventListener('click', toggleDetails);
  $('theme').addEventListener('click', () => {document.body.classList.toggle('dark'); storage.set('codex-history-theme', document.body.classList.contains('dark') ? 'dark' : 'light');});
  document.addEventListener('keydown', event => {
    if (event.isComposing) return;
    const editing = ['INPUT', 'TEXTAREA'].includes(event.target.tagName) || event.target.isContentEditable;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {event.preventDefault(); if (!$('picker').open) openPicker();}
    else if (!editing && event.key === '/' && !$('picker').open) {event.preventDefault(); openPicker();}
    else if ((event.ctrlKey || event.altKey) && event.key.toLowerCase() === 'h') {event.preventDefault(); toggleDetails();}
  });

  function notice(text, action) {
    $('notice').hidden = false; $('notice').replaceChildren(document.createTextNode(text));
    if (action) {const button = document.createElement('button'); button.textContent = 'Load new messages'; button.addEventListener('click', action); $('notice').append(button);}
  }
  function applyPending() {if (state.pending) {render(state.pending); state.pending = null;} $('notice').hidden = true;}
  let fetching = false;
  async function refresh(manual = false) {
    if (embedded) {
      if (!state.data) {
        render(JSON.parse(embedded.textContent));
        $('refresh').hidden = true;
        if (state.data.questions.length) openPicker();
      }
      return;
    }
    if (fetching) return;
    fetching = true;
    try {
      const response = await fetch('/api/history?token=' + encodeURIComponent(token), {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'The local viewer is unavailable.');
      if (!state.data) {render(data); $('notice').hidden = true; if (data.questions.length) openPicker();}
      else if (data.revision !== state.data.revision) {
        state.pending = data;
        if (manual) applyPending(); else notice('New messages are available. Your reading position has been kept.', applyPending);
      } else if (manual) {$('notice').hidden = true;}
    } catch (error) {notice('Cannot refresh. Your loaded conversation is still here. Reopen the viewer if its two-hour session has ended. ' + error.message);}
    finally {fetching = false;}
  }
  $('refresh').addEventListener('click', () => refresh(true));
  refresh();
  if (!embedded) setInterval(() => {if (!document.hidden) refresh();}, 5000);
})();
