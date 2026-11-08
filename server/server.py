#!/usr/bin/env python3
"""Servidor de sincronização do Prazo Online.

Guarda apenas blocos CIFRADOS (o servidor nunca vê tarefas nem a frase secreta).
Sem dependências: só Python 3. Coloque atrás de HTTPS (Caddy, nginx, Cloudflare
Tunnel...) — o app online só aceita endereços https://.

    python3 server/server.py --port 8080 --data ./dados
"""
import argparse
import json
import os
import re
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOM = re.compile(r"^/v1/rooms/([0-9a-f]{64})$")
MAX_BODY = 5 * 1024 * 1024
MAX_ROOMS = 1000
RATE = 60  # requisições por minuto por IP

lock = threading.Lock()
hits = defaultdict(list)


class Handler(BaseHTTPRequestHandler):
    data_dir = "."

    def log_message(self, *a):  # sem logs com IPs/salas
        pass

    def _send(self, code, obj=None):
        body = json.dumps(obj if obj is not None else {}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _limited(self):
        ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        now = time.time()
        with lock:
            hits[ip] = [t for t in hits[ip] if now - t < 60]
            hits[ip].append(now)
            return len(hits[ip]) > RATE

    def _room_path(self):
        m = ROOM.match(self.path)
        return os.path.join(self.data_dir, m.group(1) + ".json") if m else None

    def do_GET(self):
        path = self._room_path()
        if not path:
            return self._send(404)
        if self._limited():
            return self._send(429)
        with lock:
            if not os.path.exists(path):
                return self._send(404)
            with open(path) as f:
                return self._send(200, json.load(f))

    def do_PUT(self):
        path = self._room_path()
        if not path:
            return self._send(404)
        if self._limited():
            return self._send(429)
        n = int(self.headers.get("Content-Length", "0"))
        if n <= 0 or n > MAX_BODY:
            return self._send(413)
        try:
            req = json.loads(self.rfile.read(n))
            base, blob = int(req["base"]), str(req["blob"])
        except Exception:
            return self._send(400)
        with lock:
            cur = 0
            if os.path.exists(path):
                with open(path) as f:
                    cur = json.load(f)["version"]
            elif len(os.listdir(self.data_dir)) >= MAX_ROOMS:
                return self._send(507)
            if base != cur:
                return self._send(409, {"version": cur})
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"version": cur + 1, "blob": blob}, f)
            os.replace(tmp, path)
        self._send(200, {"version": cur + 1})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--data", default="./dados")
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    os.makedirs(a.data, exist_ok=True)
    Handler.data_dir = a.data
    print(f"Prazo server em http://{a.host}:{a.port} (coloque atrás de HTTPS)")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
