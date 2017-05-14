from common import helpers
from common.communication import *
from servent import node
from servent.node import Node


class Servent:
    def __init__(self, host, port) -> None:
        self.id = -1
        self.node = Node()
        self.num_nodes = 0
        self.bc_cnt = 0
        self.thread_lock = threading.Lock()

        self.communicator = Communicator(host, port, self.received_message)
        self.communicator.start()
        self.communicator.send(BOOTSTRAP_HOST, BOOTSTRAP_PORT, Msg.bs_new_servent)
        self.communicator.cpanel_add_node()
        self.communicator.cpanel_add_edge(BOOTSTRAP_HOST, BOOTSTRAP_PORT, False)

    def received_message(self, host, port, message):
        print("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        if tokens[0] == Msg.bs_new_servent_id:
            self.id = int(tokens[1])
            return

        if "broadcast" in tokens[0]:
            self.broadcast(message)

        while self.id == -1:
            pass

        if tokens[0] == Msg.bs_only_servent:
            self.communicator.cpanel_rm_edge(BOOTSTRAP_HOST, BOOTSTRAP_PORT)
            self.node.id = 0
            self.num_nodes = 1
        elif tokens[0] == Msg.bs_contact_servent:
            h, p = helpers.extract_host_and_port(tokens[1])
            self.contact_servent(h, p)
            if (host, port) == (BOOTSTRAP_HOST, BOOTSTRAP_PORT):
                self.communicator.cpanel_rm_edge(BOOTSTRAP_HOST, BOOTSTRAP_PORT)
        elif tokens[0] == Msg.my_child:
            self.my_child(host, port, tokens[1])
        elif tokens[0] == Msg.need_a_parent:
            self.need_a_parent(host, port)
        elif tokens[0] == Msg.broadcast_num_nodes:
            self.num_nodes = int(tokens[1])
        elif tokens[0] == Msg.connect_with:
            r_id = int(tokens[1])
            if r_id == self.node.id:
                s_id = int(tokens[2])
                self.connect_with(s_id, host, port)
            else:
                h, p = self.node.next_in_path(r_id)
                self.communicator.forward(host, port, h, p, message)
        elif tokens[0] == Msg.connect_with_me:
            self.connect_with_me(int(tokens[1]), host, port)
        else:
            print(message)

    broadcasts_cache = set()

    def broadcast(self, message):
        bc_id = message.split(" ")[-1]
        if bc_id in self.broadcasts_cache:
            return
        self.broadcasts_cache.add(bc_id)

        if self.node.parent is not None:
            h, p = self.node.parent
            self.communicator.send(h, p, message)
        if self.node.left_child is not None:
            h, p = self.node.left_child
            self.communicator.send(h, p, message)
        if self.node.right_child is not None:
            h, p = self.node.right_child
            self.communicator.send(h, p, message)
        if self.node.next is not None:
            h, p = self.node.next
            self.communicator.send(h, p, message)
        if self.node.previous is not None:
            h, p = self.node.previous
            self.communicator.send(h, p, message)

    # ------ received_message methods ------

    def contact_servent(self, host2, port2):
        self.communicator.send(host2, port2, Msg.need_a_parent)
        self.communicator.cpanel_add_edge(host2, port2, True)

    def need_a_parent(self, host, port):
        while self.node.id == -1:
            pass

        retry = True
        while retry:
            retry = False
            n = self.num_nodes
            with self.thread_lock:
                if n == node.left_child_id(self.node.id):
                    if self.node.left_child is None:
                        # init left child
                        self.node.left_child = host, port
                        left_id = node.left_child_id(self.node.id)
                        self.communicator.send(host, port, "%s %d" % (Msg.my_child, left_id))

                        # tell my left child's previous to connect with my left child
                        left_child_previous = node.previous_id(left_id)
                        if left_child_previous != -1:
                            h, p = self.node.next_in_path(left_child_previous)
                            self.communicator.forward(host, port, h, p,
                                                      "%s %d %d" % (Msg.connect_with, left_child_previous, left_id))
                    else:
                        retry = True
                elif n == node.right_child_id(self.node.id):
                    if self.node.right_child is None:
                        # init right child
                        self.node.right_child = (host, port)
                        right_i = node.right_child_id(self.node.id)
                        self.communicator.send(host, port, "%s %d" % (Msg.my_child, right_i))

                        # tell my left child to connect with right child
                        assert self.node.left_child is not None
                        h, p = self.node.left_child
                        self.communicator.forward(host, port, h, p,
                                                  "%s %d %d" % (Msg.connect_with, node.previous_id(right_i), right_i))
                    else:
                        retry = True
                else:
                    next_node = self.node.next_in_path(n)
                    if next_node is not None:
                        h, p = next_node
                        self.communicator.send(host, port, "%s (%s:%d)" % (Msg.bs_contact_servent, h, p))
                    else:
                        retry = True

    def my_child(self, host, port, node_id):
        with self.thread_lock:
            self.node.id = int(node_id)
            self.num_nodes = self.node.id + 1
            self.node.parent = host, port
            self.bc_cnt += 1
            bc_id = "%d:%d" % (self.id, self.bc_cnt)
            message = "%s %d %s" % (Msg.broadcast_num_nodes, self.node.id + 1, bc_id)
            self.broadcast(message)

    def connect_with(self, node_id, host, port):
        if node_id == node.previous_id(self.node.id):
            self.node.previous = host, port
            self.communicator.send(host, port, "%s %d" % (Msg.connect_with_me, self.node.id))
        elif node_id == node.next_id(self.node.id):
            self.node.next = host, port
            self.communicator.send(host, port, "%s %d" % (Msg.connect_with_me, self.node.id))

    def connect_with_me(self, node_id, host, port):
        if node_id == node.previous_id(self.node.id):
            self.node.previous = host, port
        elif node_id == node.next_id(self.node.id):
            self.node.next = host, port


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-ho", "--host", dest="host", type=str, default="localhost")
    parser.add_argument("-p", "--port", dest="port", type=int, required=True)
    args = parser.parse_args()
    Servent(args.host, args.port)
