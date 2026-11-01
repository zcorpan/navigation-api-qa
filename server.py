"""Static server for the repo on 127.0.0.1:8765, plus /slow?ms=N (HTML after N ms) and
/status?code=N (empty response with that status)."""
import functools, http.server, os, time
from urllib.parse import parse_qs, urlsplit


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlsplit(self.path)
        q = parse_qs(u.query)
        if u.path == '/slow':
            time.sleep(int(q.get('ms', ['1000'])[0]) / 1000)
            body = b'<!doctype html><title>slow page</title><p>slow page'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == '/status':
            self.send_response(int(q.get('code', ['204'])[0]))
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        super().do_GET()


http.server.ThreadingHTTPServer(('127.0.0.1', 8765), functools.partial(H, directory=os.path.dirname(os.path.abspath(__file__)))).serve_forever()
