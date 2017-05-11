from servent.communication import Communicator, Msg

BOOTSTRAP_HOST = "localhost"
BOOTSTRAP_PORT = 8970


class Bootstrap:
    def __init__(self) -> None:
        super().__init__()
        self.communicator = Communicator(BOOTSTRAP_HOST, BOOTSTRAP_PORT, self.received_message)
        self.communicator.start()
        self.servent_id = 0
        self.job_id = 0
        self.servents = {}

    def received_message(self, host, port, message):
        print("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        if tokens[0] == Msg.BS_HI:
            self.servent_id += 1
            i = self.servent_id
            self.servents[i] = (host, port)
            self.communicator.send(host, port, "%s %d" % (Msg.BS_YOUR_ID, i))
        elif tokens[0] == Msg.BS_BYE:
            i = int(tokens[1])
            self.servents.pop(i)
        elif tokens[0] == Msg.BS_NEW_JOB:
            self.job_id += 1
            i = self.job_id
            self.communicator.send(host, port, "%s %d" % (Msg.BS_NEW_JOB_ID, i))


if __name__ == '__main__':
    Bootstrap()
    print("Bootstrap listening on port %d" % BOOTSTRAP_PORT)
