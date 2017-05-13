import random
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
import re
import time

BOOTSTRAP_HOST = "localhost"
BOOTSTRAP_PORT = 8970
CPANEL_HOST = "localhost"
CPANEL_PORT = 8971


class Communicator(Thread):
    def __init__(self, host, listen_port, delegate_method) -> None:
        super().__init__()
        self.server_socket = socket.socket()
        self.host = host
        self.listen_port = listen_port
        self.active = True
        self.delegate_method = delegate_method

    def run(self) -> None:
        super().run()
        self.server_socket.bind((self.host, self.listen_port))
        self.server_socket.listen(15)  # become a server socket, maximum 5 connections

        executor = ThreadPoolExecutor(max_workers=10)
        while self.active:
            client_socket, address = self.server_socket.accept()
            executor.submit(self.receive_message, client_socket)
        executor.shutdown()

    def send(self, host, port, message) -> None:
        time.sleep(random.randint(1, 10) * 0.1)
        try:
            client_socket = socket.socket()
            client_socket.connect((host, port))
            data = ("(%s:%d) %s" % (self.host, self.listen_port, message)).encode()
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

            r = re.compile('\((.*):(\d+)\) (.*)')
            groups = r.match(message.decode()).groups()
            if groups:
                host = groups[0]
                port = int(groups[1])
                message = groups[2]
            else:
                return

            self.delegate_method(host, port, message)
        except Exception as e:
            print(e)
            raise


class Msg:
    bs_new_servent = "new_servent"
    bs_new_servent_id = "new_servent_id"
    bs_quit = "quit"
    bs_only_servent = "only_servent"
    bs_contact_servent = "contact_servent"
    bs_new_job = "new_job"
    bs_new_job_id = "bs_new_job_id"
