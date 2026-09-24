"""Build a portable HTML snapshot with local fonts/scripts and no runtime server."""

import base64
import json
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def build_html(data):
    html = (ASSETS / "viewer.html").read_text(encoding="utf-8")

    def style(match):
        path = ASSETS / match.group(1)
        css = path.read_text(encoding="utf-8")
        def font(match):
            filename = match.group(1)
            asset = path.parent / filename
            mime = {"woff2": "font/woff2", "woff": "font/woff", "ttf": "font/ttf"}[asset.suffix[1:]]
            return 'url("data:{};base64,{}")'.format(mime, base64.b64encode(asset.read_bytes()).decode())
        css = re.sub(r'url\(["\']?(fonts/[^)"\']+)["\']?\)', font, css)
        return "<style>" + css + "</style>"

    html = re.sub(r'<link rel="stylesheet" href="/([^?]+)\?token=__TOKEN__">', style, html)
    scripts = []
    def script(match):
        scripts.append((ASSETS / match.group(1)).read_text(encoding="utf-8"))
        return ""
    html = re.sub(r'<script defer src="/([^?]+)\?token=__TOKEN__"></script>', script, html)
    safe_data = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    payload = '<script id="history-data" type="application/json">' + safe_data + '</script>'
    payload += "\n".join('<script>' + body.replace('</script', '<\\/script') + '</script>' for body in scripts)
    return html.replace("</body>", payload + "</body>")
