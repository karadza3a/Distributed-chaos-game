import argparse
import logging
import random
import threading
from common.communication import Communicator, Msg
from common.config import *


class Bootstrap:
    def __init__(self) -> None:
        super().__init__()
        self.thread_lock = threading.Lock()
        self.communicator = Communicator(BOOTSTRAP_HOST, BOOTSTRAP_PORT, self.received_message, self.quitting)
        self.communicator.start()
        self.servent_id = 0
        self.servents = {}
        if ENABLE_CPANEL:
            self.communicator.send(CPANEL_HOST, CPANEL_PORT, "0 add_bs")

    def quitting(self):
        self.communicator.cpanel_rm_node()

    def received_message(self, host, port, message):
        logging.info("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        if tokens[0] == Msg.bs_new_servent:
            first = None
            with self.thread_lock:
                self.servent_id += 1
                i = self.servent_id
                if len(self.servents) > 0:
                    first = self.servents[random.choice(list(self.servents.keys()))]
                self.servents[i] = (host, port)
            self.communicator.send(host, port, "%s %d" % (Msg.bs_new_servent_id, i))
            if first is None:
                self.communicator.send(host, port, Msg.bs_only_servent)
            else:
                self.communicator.send(host, port, "%s (%s:%d)" % (Msg.bs_contact_servent, first[0], first[1]))
        elif tokens[0] == Msg.bs_quit:
            with self.thread_lock:
                i = int(tokens[1])
                self.servents.pop(i)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log_file", dest="log_file", type=str, required=True)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=logging.DEBUG, filemode="w")

    b = Bootstrap()
    print("Bootstrap listening on port %d..." % BOOTSTRAP_PORT)

    while True:
        input_cmd = input("q to quit:")
        if input_cmd == "q":
            break

    print("Quitting...")
    b.communicator.active = False
    b.communicator.join(100)
    print("bye")


if __name__ == '__main__':
    main()
