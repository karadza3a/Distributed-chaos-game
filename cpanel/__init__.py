import re
from common.communication import Communicator, CPANEL_HOST, CPANEL_PORT
import networkx as nx
import matplotlib.pyplot as plt


class CPanel:
    def __init__(self) -> None:
        super().__init__()
        self.communicator = Communicator(CPANEL_HOST, CPANEL_PORT, self.received_message)
        self.communicator.start()
        self.graph = nx.Graph()
        self.vertices = {}
        self.display_graph()

    def received_message(self, host, port, message):
        print(message)
        n_id = "%s:%d" % (host, port)
        if message == "add_bs":
            self.graph.add_node(n_id, {'node_type': "Bootstrap"})
        elif message == "add_node":
            self.graph.add_node(n_id, {'node_type': "Servent"})
        elif "add_edge" in message:
            r = re.compile('add_edge \((.*):(\d+)\)')
            groups = r.match(message).groups()
            host2 = groups[0]
            port2 = int(groups[1])
            n2_id = "%s:%d" % (host2, port2)
            self.graph.add_edge(n_id, n2_id)

    def display_graph(self):
        plt.ion()
        plt.show()
        while True:
            try:
                plt.clf()
                graph_copy = nx.Graph(self.graph)
                pos1 = nx.circular_layout(graph_copy)
                nx.draw_networkx(graph_copy, pos1)
            finally:
                plt.pause(0.5)


if __name__ == '__main__':
    CPanel()
    print("CPanel listening on port %d" % CPANEL_PORT)

# # Create a node with a custom_property
# node_a = graph.Node("A", custom_property=1)
#
# # Create a node and then add the custom_property
# node_b = graph.Node("B")
# node_b.property['custom_property'] = 2
#
# # Add the node to the stream
# # you can also do it one by one or via a list
# # l = [node_a,node_b]
# # stream.add_node(*l)
# stream.add_node(node_a, node_b)
#
# # Create edge
# # You can also use the id of the node : graph.Edge("A","B",custom_property="hello")
# edge_ab = graph.Edge(node_a, node_b, custom_property="hello")
# stream.add_edge(edge_ab)
