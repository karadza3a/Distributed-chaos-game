import logging
import random
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from common.config import *


class Communicator(Thread):
    def __init__(self, host, listen_port, received_delegate, quit_delegate) -> None:
        super().__init__()
        self.server_socket = socket.socket()
        self.host = host
        self.listen_port = listen_port
        self.active = True
        self.received_delegate = received_delegate
        self.quit_delegate = quit_delegate

    def run(self) -> None:
        super().run()
        self.server_socket.bind((self.host, self.listen_port))
        self.server_socket.listen(30)

        executor = ThreadPoolExecutor(max_workers=50)
        self.server_socket.settimeout(2)
        while self.active:
            try:
                client_socket, address = self.server_socket.accept()
                executor.submit(self.receive_message, client_socket)
            except socket.timeout:
                pass
        self.quit_delegate()
        self.server_socket.close()
        executor.shutdown()

    def forward(self, from_host, from_port, to_host, to_port, message) -> None:
        self._raw_send(from_host, from_port, to_host, to_port, message)

    def send(self, host, port, message) -> None:
        self._raw_send(self.host, self.listen_port, host, port, message)

    @staticmethod
    def _raw_send(from_host, from_port, to_host, to_port, message) -> None:
        try:
            client_socket = socket.socket()
            client_socket.connect((to_host, to_port))
            data = ("(%s:%d) %s" % (from_host, from_port, message)).encode()
            client_socket.sendall(data)
            client_socket.shutdown(socket.SHUT_WR)

            buf = client_socket.recv(16)
            client_socket.close()
            if buf != b"ack\n":
                raise ConnectionError("Ack not received!")
        except Exception:
            logging.exception("Error sending!")
            raise

    def receive_message(self, sock) -> None:
        time.sleep(random.randint(1, 50) * 0.01)
        message = b""
        try:
            while True:
                buf = sock.recv(1024)
                if len(buf) > 0:
                    message += buf
                else:
                    break
            sock.sendall(b"ack\n")
            sock.close()

            r = re.compile('\((.*):(\d+)\) (.*)')
            groups = r.match(message.decode()).groups()
            if groups:
                host = groups[0]
                port = int(groups[1])
                message = groups[2]
            else:
                return

            self.received_delegate(host, port, message)
        except Exception:
            logging.exception("Error receiving!")
            raise

    cpanel_message_id = 0
    cpanel_message_lock = threading.Lock()

    def cpanel_add_node(self):
        if ENABLE_CPANEL:
            with self.cpanel_message_lock:
                msg_id = self.cpanel_message_id
                self.cpanel_message_id += 1
            self.send(CPANEL_HOST, CPANEL_PORT, "%d add_node" % msg_id)

    def cpanel_rm_node(self):
        if ENABLE_CPANEL:
            with self.cpanel_message_lock:
                msg_id = self.cpanel_message_id
                self.cpanel_message_id += 1
            self.send(CPANEL_HOST, CPANEL_PORT, "%d rm_node" % msg_id)

    def cpanel_add_edge(self, host2, port2, temp):
        if ENABLE_CPANEL:
            with self.cpanel_message_lock:
                msg_id = self.cpanel_message_id
                self.cpanel_message_id += 1
            t = "t" if temp else "p"
            self.send(CPANEL_HOST, CPANEL_PORT, "%d add_edge %s %s:%d" % (msg_id, t, host2, port2))

    def cpanel_rm_edge(self, host2, port2):
        if ENABLE_CPANEL:
            with self.cpanel_message_lock:
                msg_id = self.cpanel_message_id
                self.cpanel_message_id += 1
            self.send(CPANEL_HOST, CPANEL_PORT, "%d rm_edge %s:%d" % (msg_id, host2, port2))

    def cpanel_node_id(self, node_id):
        if ENABLE_CPANEL:
            with self.cpanel_message_lock:
                msg_id = self.cpanel_message_id
                self.cpanel_message_id += 1
            self.send(CPANEL_HOST, CPANEL_PORT, "%d node_id %d" % (msg_id, node_id))

    @staticmethod
    def cpanel_input_command(msg):
        with Communicator.cpanel_message_lock:
            msg_id = Communicator.cpanel_message_id
            Communicator.cpanel_message_id += 1
        Communicator._raw_send("input", 0, CPANEL_HOST, CPANEL_PORT, "%d input_cmd %s" % (msg_id, msg))


class Msg:
    bs_new_servent = "new_servent"
    bs_new_servent_id = "new_servent_id"
    bs_quit = "quit"
    bs_only_servent = "only_servent"
    bs_contact_servent = "contact_servent"
    need_a_parent = "need_a_parent"
    my_child = "my_child"
    connect_with = "connect_with"
    connect_with_me = "connect_with_me"
    broadcast_num_nodes = "broadcast_num_nodes"
    broadcast_new_job = "broadcast_new_job"
    broadcast_remove_job = "broadcast_remove_job"
    broadcast_show_job = "broadcast_show_job"
    job_data = "job_data"
    job_data_reassign = "job_data_reassign"
    active_jobs = "active_jobs"
