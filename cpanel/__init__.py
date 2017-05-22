import argparse
import threading
import logging
import matplotlib.pyplot as plt
import networkx as nx
from common.communication import Communicator
from common.config import *
from servent import node_tools


class CPanel:
    def __init__(self) -> None:
        super().__init__()
        self.delay = 0.05
        self.show = False
        self.communicator = Communicator(CPANEL_HOST, CPANEL_PORT, self.received_message, self.quitting)
        self.communicator.start()
        self.graph = nx.Graph()
        self.vertices = {}

    last_message_id = {}

    def quitting(self):
        pass

    def received_message(self, host, port, message):
        logging.info("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        n_id = "%s:%d" % (host, port)

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
        elif "rm_node" in message:
            self.graph.remove_node(n_id)
        elif "input_cmd" in message:
            self.input_command(message.replace("%d input_cmd " % m_id, ""))

    def display_graph(self):
        plt.rcParams['axes.facecolor'] = 'black'

        while self.communicator.active:
            plt.ion()
            plt.show()
            while self.show and self.communicator.active:
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
                    plt.pause(self.delay)
            plt.ioff()
            while not self.show and self.communicator.active:
                plt.pause(0.5)
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

    def input_command(self, input_cmd):
        try:
            if input_cmd == "q":
                self.communicator.active = False
                print("bye")
                return True
            elif input_cmd == "resume":
                self.show = True
            elif input_cmd == "pause":
                self.show = False
            elif "delay" in input_cmd:
                self.delay = float(input_cmd.split(" ")[1])
            else:
                print("unrecognized")
                return False
            print("ok")
            return False
        except Exception as e:
            logging.exception(e)

    def input_loop(self):
        while True:
            input_cmd = input("q to quit:")
            should_quit = self.input_command(input_cmd)
            if should_quit:
                break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log_file", dest="log_file", type=str, required=True)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=logging.DEBUG, filemode="w")

    c = CPanel()
    print("CPanel listening on port %d..." % CPANEL_PORT)
    input_thread = threading.Thread(target=c.input_loop)
    input_thread.start()
    try:
        c.display_graph()  # this will return only when stopped (active == False) or in case an exception is thrown
    except Exception as e:
        logging.exception("Display error:" + str(e))
    c.communicator.active = False  # this should already be set to False, but just in case any exception is thrown
    c.communicator.join(100)


if __name__ == '__main__':
    main()
