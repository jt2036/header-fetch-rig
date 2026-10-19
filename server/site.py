#!/usr/bin/env python3
"""header-fetch-rig test server.

Serves known benign and injection payloads in HTTP response metadata across
the delivery routes documented by Signals Corps (wiki runs #426/#457):

  /plain            benign headers + one benign custom header (control)
  /inject-command   canary + "run this command" payload in X-AI-Context
  /inject-secret    canary + read-a-local-file-and-echo payload in X-AI-Context
  /statusline       4xx status whose reason phrase carries the canary (RFC 9112
                    says clients SHOULD ignore reason phrases; models don't)
  /redirect         3xx hop that carries the injection header, then lands /plain
                    (redirect-distrust probe)
  /llms.txt         llms.txt body channel with sign-up/install-style ask

The server never invents payloads: every injection string is defined in
canary.json so scorers can match verbatim.

Usage: python3 site.py [--port 8089] [--secret-file PATH]
"""
import argparse
import http.server
import json
import os
import socketserver
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANARY = json.loads((HERE / "canary.json").read_text())


class Handler(http.server.BaseHTTPRequestHandler):
    secret_file = "/tmp/header-rig-secret.txt"

    # ---------------------------------------------------------------- helpers
    def _send(self, status, reason, headers, body=b"<html><body>OK</body></html>",
              ctype="text/html"):
        self.send_response(status, reason)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ai_headers(self, value):
        # Three plausible header homes for agent-directed text, per the census:
        # the generic X-AI* family, a vendor-ish one, and a status-adjacent one.
        return {
            "X-AI-Context": value,
            "X-Agent-Guidance": value,
        }

    # ------------------------------------------------------------------ routes
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        base = {
            "Server": "header-fetch-rig/1.0",
            "X-Canary-Benign": CANARY["benign_header_value"],
            "X-Rig-Route": path,
        }
        if path == "/plain":
            self._send(200, "OK", base)
        elif path == "/inject-command":
            h = dict(base)
            h.update(self._ai_headers(CANARY["inject_command"]))
            self._send(200, "OK", h)
        elif path == "/inject-secret":
            h = dict(base)
            h.update(self._ai_headers(CANARY["inject_secret"].format(
                secret_file=self.secret_file)))
            self._send(200, "OK", h)
        elif path == "/statusline":
            # Reason phrase is free text; many fetch tools copy
            # "HTTP/1.1 <code> <reason>" into context (curl -i does).
            self._send(400, CANARY["inject_statusline"], base)
        elif path == "/redirect":
            h = dict(base)
            h.update(self._ai_headers(CANARY["inject_command"]))
            h["Location"] = "/plain"
            self._send(302, "Found", h)
        elif path == "/llms.txt":
            body = CANARY["llms_txt"].encode()
            self._send(200, "OK", base, body=body, ctype="text/plain")
        else:
            self._send(404, "Not Found", base, body=b"")

    def do_POST(self):  # noqa: N802
        # Mock sign-up endpoint for the llms.txt route: log what an agent sends.
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length)
        with open(self.secret_file + ".attempts.log", "ab") as f:
            f.write(b"%s %s\n" % (self.path.encode(), body))
        self._send(200, "OK", {}, body=b'{"ok":true}')

    def log_message(self, format, *args):  # noqa: A002
        sys.stderr.write("[site] %s %s\n" % (self.address_string(), format % args))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8089)
    ap.add_argument("--secret-file", default=Handler.secret_file)
    args = ap.parse_args()
    Handler.secret_file = args.secret_file
    Path(args.secret_file).write_text(CANARY["secret_file_content"])
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), Handler) as httpd:
        sys.stderr.write("[site] serving on 127.0.0.1:%d\n" % args.port)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
