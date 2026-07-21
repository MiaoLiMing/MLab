import socket
import threading

LISTEN = ("127.0.0.1", 19080)
TARGET = ("104.16.24.34", 443)


def relay(source: socket.socket, target: socket.socket) -> None:
    try:
        while data := source.recv(64 * 1024):
            target.sendall(data)
    except OSError:
        pass
    finally:
        for item in (source, target):
            try:
                item.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            item.close()


def handle(client: socket.socket) -> None:
    try:
        request = b""
        while b"\r\n\r\n" not in request and len(request) < 16_384:
            request += client.recv(4096)
        first_line = request.split(b"\r\n", 1)[0].decode("ascii", "ignore")
        if not first_line.startswith("CONNECT registry.npmjs.org:"):
            client.close()
            return
        upstream = socket.create_connection(TARGET, timeout=15)
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        remainder = request.split(b"\r\n\r\n", 1)[1]
        if remainder:
            upstream.sendall(remainder)
        threading.Thread(target=relay, args=(client, upstream), daemon=True).start()
        relay(upstream, client)
    except OSError:
        client.close()


with socket.create_server(LISTEN, backlog=32) as server:
    print("npm-connect-proxy listening on 127.0.0.1:19080", flush=True)
    while True:
        connection, _ = server.accept()
        threading.Thread(target=handle, args=(connection,), daemon=True).start()
