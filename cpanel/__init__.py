import argparse
import threading

import logging
import matplotlib.pyplot as plt
import networkx as nx
from common.communication import Communicator, CPANEL_HOST, CPANEL_PORT
from servent import node_tools


class CPanel:
    def __init__(self) -> None:
        super().__init__()
        self.communicator = Communicator(CPANEL_HOST, CPANEL_PORT, self.received_message)
        self.communicator.start()
        self.graph = nx.Graph()
        self.vertices = {}

    last_message_id = {}

    def received_message(self, host, port, message):
        logging.info("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        n_id = "(%s:%d)" % (host, port)

        m_id = int(tokens[0])
        if n_id not in self.last_message_id:
            self.last_message_id[n_id] = -1
        while self.last_message_id[n_id] != m_id - 1:
            pass
        self.last_message_id[n_id] = m_id

        if "add_bs" in message:
            self.graph.add_node(n_id, {'node_type': "Bootstrap"})
        elif "add_node" in message:
            self.graph.add_node(n_id, {'node_type': "Servent"})
        elif "node_id" in message:
            self.graph.node[n_id]['id'] = int(tokens[2])
        elif "add_edge" in message:
            temp = tokens[2] == "t"
            n2_id = tokens[3]
            self.graph.add_edge(n_id, n2_id, {'temp_edge': temp})
        elif "rm_edge" in message:
            n2_id = tokens[2]
            self.graph.remove_edge(n_id, n2_id)

    def display_graph(self):
        plt.ion()
        plt.rcParams['axes.facecolor'] = 'black'
        plt.show()
        while c.communicator.active:
            try:
                plt.clf()
                graph_copy = nx.Graph(self.graph)
                pos1 = self.custom_layout(graph_copy)
                nx.draw_networkx(graph_copy, pos1, node_color="b", font_color="w",
                                 labels={node: node[-5:] for node in graph_copy},
                                 edge_color=["b" if graph_copy[u][v]['temp_edge'] else "g" for u, v in
                                             graph_copy.edges()])
                plt.xlim(-0.2, 2.2)
                plt.ylim(-0.2, 1.2)
            finally:
                plt.pause(0.05)
        plt.ioff()
        plt.close("all")

    @staticmethod
    def custom_layout(graph) -> dict:
        positions = {}
        nodes = graph.nodes_iter(True)
        bs = None
        tree = []
        pending = []
        for node, properties in nodes:
            if properties["node_type"] == "Bootstrap":
                bs = node
            elif "id" in properties:
                tree.append((properties["id"], node))
            else:
                pending.append(node)

        tree.sort()
        pending.sort()

        positions[bs] = 0, 1

        if len(pending) > 0:
            delta = 1 / (len(pending) - 1) if len(pending) > 5 else 0.25
            current = 0
            for node in pending:
                positions[node] = 1 - (current * current), 0.9 - current
                current += delta

        if len(tree) == 0:
            return positions

        num_levels = node_tools.level(tree[-1][0])
        delta_y = 1 / (num_levels - 1) if num_levels > 5 else 0.25
        current_y = 0
        delta_x = 1
        current_x = 0.5
        nodes_per_level = 1
        tree_positions = {}
        for i in range(tree[-1][0] + 1):
            if i >= nodes_per_level:
                nodes_per_level += nodes_per_level + 1
                current_y += delta_y
                delta_x = delta_x / 2
                current_x = delta_x / 2
            tree_positions[i] = 1 + current_x, 1 - current_y
            current_x += delta_x

        for node_id, node in tree:
            positions[node] = tree_positions[node_id]

        return positions

    def input_loop(self):
        while True:
            input_cmd = input("q to quit:")
            if input_cmd == "q":
                break

        print("Quitting...")
        self.communicator.active = False
        print("bye")


class Mock:
    msgs = [
        ("localhost", 8970, "0 add_bs"),
        ("localhost", 9001, "0 add_node"),
        ("localhost", 9006, "0 add_node"),
        ("localhost", 9005, "0 add_node"),
        ("localhost", 9000, "0 add_node"),
        ("localhost", 9003, "0 add_node"),
        ("localhost", 9004, "0 add_node"),
        ("localhost", 9002, "0 add_node"),
        ("localhost", 9001, "1 add_edge t (localhost:8970)"),
        ("localhost", 9005, "1 add_edge t (localhost:8970)"),
        ("localhost", 9002, "1 add_edge t (localhost:8970)"),
        ("localhost", 9000, "1 add_edge t (localhost:8970)"),
        ("localhost", 9003, "1 add_edge t (localhost:8970)"),
        ("localhost", 9006, "1 add_edge t (localhost:8970)"),
        ("localhost", 9004, "1 add_edge t (localhost:8970)"),
        ("localhost", 9003, "2 rm_edge (localhost:8970)"),
        ("localhost", 9005, "2 node_id 0"),
        ("localhost", 9000, "2 rm_edge (localhost:8970)"),
        ("localhost", 9001, "2 rm_edge (localhost:8970)"),
        ("localhost", 9001, "3 add_edge t (localhost:9003)"),
        ("localhost", 9005, "3 rm_edge (localhost:8970)"),
        ("localhost", 9006, "2 rm_edge (localhost:8970)"),
        ("localhost", 9004, "2 rm_edge (localhost:8970)"),
        ("localhost", 9003, "3 add_edge t (localhost:9005)"),
        ("localhost", 9002, "2 rm_edge (localhost:8970)"),
        ("localhost", 9004, "3 add_edge t (localhost:9000)"),
        ("localhost", 9002, "3 add_edge t (localhost:9003)"),
        ("localhost", 9000, "3 add_edge t (localhost:9003)"),
        ("localhost", 9006, "3 add_edge t (localhost:9002)"),
        ("localhost", 9003, "4 rm_edge (localhost:9005)"),
        ("localhost", 9003, "5 add_edge p (localhost:9005)"),
        ("localhost", 9003, "6 node_id 1"),
        ("localhost", 9001, "4 rm_edge (localhost:9003)"),
        ("localhost", 9000, "4 rm_edge (localhost:9003)"),
        ("localhost", 9002, "4 rm_edge (localhost:9003)"),
        ("localhost", 9001, "5 add_edge t (localhost:9005)"),
        ("localhost", 9000, "5 add_edge t (localhost:9005)"),
        ("localhost", 9002, "5 add_edge t (localhost:9005)"),
        ("localhost", 9001, "6 rm_edge (localhost:9005)"),
        ("localhost", 9001, "7 add_edge p (localhost:9005)"),
        ("localhost", 9001, "8 node_id 2"),
        ("localhost", 9002, "6 rm_edge (localhost:9005)"),
        ("localhost", 9000, "6 rm_edge (localhost:9005)"),
        ("localhost", 9000, "7 add_edge t (localhost:9001)"),
        ("localhost", 9002, "7 add_edge t (localhost:9001)"),
        ("localhost", 9000, "8 rm_edge (localhost:9001)"),
        ("localhost", 9002, "8 rm_edge (localhost:9001)"),
        ("localhost", 9002, "9 add_edge t (localhost:9005)"),
        ("localhost", 9000, "9 add_edge t (localhost:9005)"),
        ("localhost", 9002, "10 rm_edge (localhost:9005)"),
        ("localhost", 9000, "10 rm_edge (localhost:9005)"),
        ("localhost", 9002, "11 add_edge t (localhost:9001)"),
        ("localhost", 9000, "11 add_edge t (localhost:9001)"),
    ]

    c = None

    def next_message(self, i):
        self.c.received_message(*self.msgs[i])

    def while_messages(self):
        while self.c is None:
            pass
        i = 0
        while i < len(self.msgs):
            t2 = threading.Thread(target=self.next_message(i))
            t2.start()
            i += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log_file", dest="log_file", type=str, required=True)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=logging.DEBUG, filemode="w")

    c = CPanel()
    print("CPanel listening on port %d..." % CPANEL_PORT)
    input_thread = threading.Thread(target=c.input_loop)
    input_thread.start()
    c.display_graph()  # this will return only when stopped (active == false)
    c.communicator.join(100)

    # m = Mock()
    # import threading
    # t1 = threading.Thread(target=m.while_messages)
    # t1.start()
    # m.c = CPanel()
    # m.c.display_graph()
