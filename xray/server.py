"""Sarah X-ray server.   python xray/server.py [--port 8765]   then open http://localhost:8765
Uses only the standard library.  Default LLM mode = 'stub' (instant, never touches Ollama), switch in the UI to use the real model."""
import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from session import Session            # noqa: E402

SHARED = os.path.normpath(os.path.join(HERE, "..", "..", "simulations", "shared"))
S = Session()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):          # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, default=str).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/state":
            return self._send(200, S.snapshot())
        if u.path == "/events":
            return self._send(200, S.events_since(int(parse_qs(u.query).get("since", ["0"])[0])))
        base, rel = (SHARED, u.path[len("/shared/"):]) if u.path.startswith("/shared/") else (os.path.join(HERE, "web"), u.path.lstrip("/") or "index.html")
        fp = os.path.normpath(os.path.join(base, rel))
        if not fp.startswith(base) or not os.path.isfile(fp):
            return self._send(404, {"error": "not found"})
        self._send(200, open(fp, "rb").read(), mimetypes.guess_type(fp)[0] or "application/octet-stream")

    def do_POST(self):
        if self.path == "/control":
            n = int(self.headers.get("Content-Length", 0))
            return self._send(200, S.control(json.loads(self.rfile.read(n) or b"{}")))
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    print(f"Sarah X-ray on http://localhost:{a.port}  (LLM mode 'stub' by default - Ollama untouched)")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
