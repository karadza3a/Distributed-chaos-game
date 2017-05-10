from servent.communication import Communicator


class Servent:
    def __init__(self, port) -> None:
        super().__init__()
        self.communicator = Communicator(port, self)
        self.communicator.start()
        if port != 9001:
            self.communicator.send(9001, "ping")

    def received_message(self, port, message):
        if "ping" in message:
            self.communicator.send(port, "pong")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest="port", type=int, required=True)
    args = parser.parse_args()
    Servent(args.port)
