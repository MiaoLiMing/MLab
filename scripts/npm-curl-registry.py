import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN = ("127.0.0.1", 19081)
UPSTREAM = "https://registry.npmjs.org"
RESOLVE = "registry.npmjs.org:443:104.16.24.34"
LOCAL = b"http://127.0.0.1:19081/"


class RegistryHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        result = subprocess.run(
            [
                "curl.exe",
                "--silent",
                "--show-error",
                "--fail-with-body",
                "--noproxy",
                "*",
                "--resolve",
                RESOLVE,
                f"{UPSTREAM}{self.path}",
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode:
            self.send_error(502, result.stderr.decode("utf-8", "replace")[:200])
            return
        body = result.stdout
        is_tarball = "/-/" in self.path or self.path.endswith(".tgz")
        if not is_tarball:
            body = body.replace(b"https://registry.npmjs.org/", LOCAL)
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/octet-stream" if is_tarball else "application/json"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


ThreadingHTTPServer(LISTEN, RegistryHandler).serve_forever()
