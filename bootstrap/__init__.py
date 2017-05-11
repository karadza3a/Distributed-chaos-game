import random
from servent.communication import Communicator, Msg
import threading

BOOTSTRAP_HOST = "localhost"
BOOTSTRAP_PORT = 8970


class Bootstrap:
    def __init__(self) -> None:
        super().__init__()
        self.thread_lock = threading.Lock()
        self.communicator = Communicator(BOOTSTRAP_HOST, BOOTSTRAP_PORT, self.received_message)
        self.communicator.start()
        self.servent_id = 0
        self.job_id = 0
        self.servents = {}

    def received_message(self, host, port, message):
        print("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        if tokens[0] == Msg.bs_new_servent:
            first = None
            with self.thread_lock:
                self.servent_id += 1
                i = self.servent_id
                self.servents[i] = (host, port)
                if len(self.servents) > 0:
                    first = self.servents[random.choice(list(self.servents.keys()))]
            self.communicator.send(host, port, "%s %d" % (Msg.bs_new_servent_id, i))
            if first is None:
                self.communicator.send(host, port, Msg.bs_only_servent)
            else:
                self.communicator.send(host, port, "%s (%s:%d)" % (Msg.bs_contact_servent, first[0], first[1]))
        elif tokens[0] == Msg.bs_quit:
            with self.thread_lock:
                i = int(tokens[1])
                self.servents.pop(i)
        elif tokens[0] == Msg.bs_new_job:
            with self.thread_lock:
                self.job_id += 1
                i = self.job_id
            self.communicator.send(host, port, "%s %d" % (Msg.bs_new_job_id, i))


if __name__ == '__main__':
    Bootstrap()
    print("Bootstrap listening on port %d" % BOOTSTRAP_PORT)
