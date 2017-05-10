import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

import re


class Communicator(Thread):
    def __init__(self, listen_port, delegate) -> None:
        super().__init__()
        self.server_socket = socket.socket()
        self.listen_port = listen_port
        self.active = True
        self.delegate = delegate

    def run(self) -> None:
        super().run()
        self.server_socket.bind(('localhost', self.listen_port))
        self.server_socket.listen(15)  # become a server socket, maximum 5 connections

        executor = ThreadPoolExecutor(max_workers=10)
        while self.active:
            client_socket, address = self.server_socket.accept()
            print("acc: %s" % address[1])
            executor.submit(self.receive_message, client_socket)
        executor.shutdown()

    def send(self, port, message) -> None:
        try:
            client_socket = socket.socket()
            client_socket.connect(('localhost', port))
            data = ("%d %s" % (self.listen_port, message)).encode()
            client_socket.sendall(data)
            client_socket.shutdown(socket.SHUT_WR)

            buf = client_socket.recv(16)
            client_socket.close()
            if buf != b"ack":
                raise ConnectionError("Ack not received!")
        except Exception as e:
            print(e)
            raise

    def receive_message(self, sock) -> None:
        message = b""
        try:
            while True:
                buf = sock.recv(1024)
                if len(buf) > 0:
                    message += buf
                else:
                    break
            sock.sendall(b"ack")
            sock.close()

            r = re.compile('(\d+) (.*)')
            groups = r.match(message.decode()).groups()
            if groups:
                port = int(groups[0])
                message = groups[1]
            else:
                return

            self.delegate.received_message(port, message)
        except Exception as e:
            print(e)
            raise
