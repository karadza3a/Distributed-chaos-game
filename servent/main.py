from common.communication import Communicator, Msg, BOOTSTRAP_PORT, BOOTSTRAP_HOST, CPANEL_PORT, CPANEL_HOST


class Servent:
    def __init__(self, host, port) -> None:
        super().__init__()
        self.communicator = Communicator(host, port, self.received_message)
        self.communicator.start()
        self.communicator.send(BOOTSTRAP_HOST, BOOTSTRAP_PORT, Msg.bs_new_servent)
        self.communicator.send(CPANEL_HOST, CPANEL_PORT, "add_node")
        self.communicator.send(CPANEL_HOST, CPANEL_PORT, "add_edge (%s:%d)" % (BOOTSTRAP_HOST, BOOTSTRAP_PORT))
        self.id = -1

    def received_message(self, host, port, message):
        tokens = message.split(" ")
        if tokens[0] == Msg.bs_new_servent_id:
            self.id = int(tokens[1])
            print("Got id: %d" % self.id)
            self.communicator.send(host, port, "%s %d" % (Msg.bs_quit, self.id))
        else:
            print(message)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-ho", "--host", dest="host", type=str, default="localhost")
    parser.add_argument("-p", "--port", dest="port", type=int, required=True)
    args = parser.parse_args()
    Servent(args.host, args.port)
