from common.communication import Communicator, CPANEL_HOST, CPANEL_PORT
from common import helpers
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

    last_message_id = {}

    def received_message(self, host, port, message):
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
        elif "add_edge" in message:
            temp = tokens[2]
            n2_id = tokens[3]
            self.graph.add_edge(n_id, n2_id, {'temp_edge': temp})
        elif "rm_edge" in message:
            n2_id = tokens[2]
            self.graph.remove_edge(n_id, n2_id)

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
