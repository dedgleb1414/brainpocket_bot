"""
api/webhook.py — точка входа для Telegram webhook на Vercel.
Vercel вызывает эту функцию при каждом Update от Telegram.
"""

import json
import os
from http.server import BaseHTTPRequestHandler

from core.router import route_update


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            update = json.loads(body)
            route_update(update)
        except Exception as e:
            print(f"[webhook] error: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self):
        """Health-check — удобно для проверки деплоя."""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"BrainPocket bot is running")

    def log_message(self, *args):
        pass  # отключаем шум в логах Vercel
