"""
Embodied Daily local dev server.
- Serves static files (index.html, JS/CSS, data/daily.json).
- /api/hf/<path>   -> proxies to https://huggingface.co/api
- /api/arxiv/<path>-> proxies to https://export.arxiv.org/api
- /api/daily       -> runs the live build (HF + arXiv) and returns the JSON bundle

For production (GitHub Pages) the server is not used; the frontend loads data/daily.json
which is refreshed daily by GitHub Actions.
"""
import http.server, socketserver, sys, os, argparse, json
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'build'))

import importlib.util
spec = importlib.util.spec_from_file_location('build_daily', os.path.join(ROOT, 'build', 'build_daily.py'))
build_daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_daily)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/daily':
            return self._live_daily()
        if parsed.path.startswith('/api/hf/'):
            return self._proxy('https://huggingface.co/api', parsed.path[len('/api/hf'):], parsed.query)
        if parsed.path.startswith('/api/arxiv/'):
            return self._proxy('https://export.arxiv.org/api', parsed.path[len('/api/arxiv'):], parsed.query)
        return super().do_GET()

    def _live_daily(self):
        try:
            bundle = build_daily.build_bundle(limit=60)
            data = json.dumps(bundle, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            err = json.dumps({'error': str(e)}).encode('utf-8')
            self.send_response(502)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(err)

    def _proxy(self, base, rel, query):
        import urllib.request, urllib.error, ssl
        CTX = ssl.create_default_context()
        if not rel.startswith('/'): rel = '/' + rel
        target = base + rel + ('?'+query if query else '')
        try:
            req = urllib.request.Request(target, headers={'User-Agent':'Mozilla/5.0 EmbodiedDaily/1.0'})
            with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
                data = r.read()
                self.send_response(r.status)
                ctype = r.headers.get('Content-Type','application/octet-stream')
                self.send_header('Content-Type', ctype)
                self.send_header('Access-Control-Allow-Origin','*')
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type','text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(('{"error":"%s"}'%str(e)).encode('utf-8'))

    def log_message(self, fmt, *args):
        sys.stderr.write("[server] %s - %s\n" % (self.address_string(), fmt%args))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    args = ap.parse_args()
    os.chdir(ROOT)
    with socketserver.ThreadingTCPServer(('127.0.0.1', args.port), Handler) as httpd:
        print(f"Embodied Daily running at http://localhost:{args.port}/")
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\nShutting down.")

if __name__ == '__main__':
    main()


