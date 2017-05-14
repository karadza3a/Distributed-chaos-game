import random
import re
import socket
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

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

    def forward(self, from_host, from_port, to_host, to_port, message) -> None:
        self._raw_send(from_host, from_port, to_host, to_port, message)

    def send(self, host, port, message) -> None:
        self._raw_send(self.host, self.listen_port, host, port, message)

    @staticmethod
    def _raw_send(from_host, from_port, to_host, to_port, message) -> None:
        time.sleep(random.randint(1, 10) * 0.1)
        try:
            client_socket = socket.socket()
            client_socket.connect((to_host, to_port))
            data = ("(%s:%d) %s" % (from_host, from_port, message)).encode()
            client_socket.sendall(data)
            client_socket.shutdown(socket.SHUT_WR)

            buf = client_socket.recv(16)
            client_socket.close()
            if buf != b"ack":
                raise ConnectionError("Ack not received!")
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
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
            traceback.print_exc(file=sys.stderr)
            raise

    cpanel_message_id = 0
    cpanel_message_lock = threading.Lock()

    def cpanel_add_node(self):
        with self.cpanel_message_lock:
            msg_id = self.cpanel_message_id
            self.cpanel_message_id += 1
        self.send(CPANEL_HOST, CPANEL_PORT, "%d add_node" % msg_id)

    def cpanel_add_edge(self, host2, port2, temp):
        with self.cpanel_message_lock:
            msg_id = self.cpanel_message_id
            self.cpanel_message_id += 1
        t = "t" if temp else "p"
        self.send(CPANEL_HOST, CPANEL_PORT, "%d add_edge %s (%s:%d)" % (msg_id, t, host2, port2))

    def cpanel_rm_edge(self, host2, port2):
        with self.cpanel_message_lock:
            msg_id = self.cpanel_message_id
            self.cpanel_message_id += 1
        self.send(CPANEL_HOST, CPANEL_PORT, "%d rm_edge (%s:%d)" % (msg_id, host2, port2))


class Msg:
    bs_new_servent = "new_servent"
    bs_new_servent_id = "new_servent_id"
    bs_quit = "quit"
    bs_only_servent = "only_servent"
    bs_contact_servent = "contact_servent"
    bs_new_job = "new_job"
    bs_new_job_id = "bs_new_job_id"
    need_a_parent = "need_a_parent"
    my_child = "my_child"
    connect_with = "connect_with"
    connect_with_me = "connect_with_me"
    broadcast_num_nodes = "broadcast_num_nodes"
