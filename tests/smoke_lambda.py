"""Exercise an extracted ZIP against a local HTTP stand-in for Home Assistant.

Run with the extracted ZIP as the working directory and on PYTHONPATH.
Only a loopback socket and a temporary, fake config.json are used.
"""

import importlib.metadata
import json
import os
from pathlib import Path
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import haaska
import requests


def main():
    package_dir = Path.cwd().resolve()
    for module in (haaska, requests):
        assert Path(module.__file__).resolve().is_relative_to(package_dir), (
            "The test must import from the extracted deployment ZIP")

    directive = {"directive": {"header": {
        "namespace": "Alexa.Discovery", "name": "Discover",
        "payloadVersion": "3", "messageId": "zip-smoke-request"},
        "payload": {"scope": {
            "type": "BearerToken", "token": "fake-alexa-token"}}}}
    response = {"event": {"header": {
        "namespace": "Alexa.Discovery", "name": "Discover.Response",
        "payloadVersion": "3", "messageId": "zip-smoke-response"},
        "payload": {"endpoints": []}}}
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.path, self.headers["Authorization"],
                             json.loads(body)))
            data = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config_path = package_dir / "config.json"
    original_config = (
        config_path.read_bytes() if config_path.exists() else None)
    # Keep the mock request off any proxy inherited from the environment.
    os.environ["NO_PROXY"] = "127.0.0.1"
    try:
        config_path.write_text(json.dumps({
            "url": "http://127.0.0.1:" + str(server.server_port),
            "bearer_token": "fake-ha-token", "ssl_verify": True,
            "ssl_client": [], "debug": False,
        }))
        assert haaska.event_handler(directive, None) == response
        assert received == [("/api/alexa/smart_home",
                             "Bearer fake-ha-token", directive)]
        versions = {name: importlib.metadata.version(name) for name in (
            "requests", "urllib3", "certifi", "charset-normalizer", "idna")}
        print("ZIP smoke test passed:", sys.version.split()[0], versions)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        if original_config is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_bytes(original_config)


if __name__ == "__main__":
    main()
