"""
api/webhook.py — точка входа для Telegram webhook на Vercel.
"""

import json
import traceback
from http.server import BaseHTTPRequestHandler

from core.router import route_update


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            update = json.loads(body)
            print(f"[webhook] update: {json.dumps(update, ensure_ascii=False)[:300]}")
            route_update(update)
        except Exception as e:
            print(f"[webhook] ERROR: {e}")
            traceback.print_exc()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BrainPocket bot is running")

    def log_message(self, *args):
        pass
