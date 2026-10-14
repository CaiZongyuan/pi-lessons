"""Dependency-free local preview for cloud desktop terminals without Node on PATH."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
import os
root=Path(__file__).resolve().parents[1]
os.chdir(root/'docs/.vitepress/dist')
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  route=urlsplit(self.path).path
  if route=='/__qa-mobile':
   data=(root/'qa/mobile-harness.html').read_bytes()
   self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if not Path('.'+route).is_file() and Path('.'+route+'.html').is_file():self.path=route+'.html'
  super().do_GET()
print('Pi local preview: http://localhost:4173/',flush=True)
ThreadingHTTPServer(('127.0.0.1',4173),Handler).serve_forever()
