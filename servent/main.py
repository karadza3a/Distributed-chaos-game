import argparse
from common import helpers
from common.communication import *
from servent import node_tools, chaos
from servent.chaos import Chaos, random_points
from servent.node_tools import Node


class Servent:
    def __init__(self, host, port) -> None:
        self.id = -1
        self.node = Node()
        self.num_nodes = 0
        self.bc_cnt = 0
        self.job_cnt = 0
        self.active_jobs = None
        self.active_job_id = None
        self.need_job_data_for = None
        self.need_job_data_from = None
        self.needed_job_data = None
        self.thread_lock = threading.Lock()
        job_worker_thread = Thread(target=self.job_worker)
        job_worker_thread.start()

        self.communicator = Communicator(host, port, self.received_message, self.quitting)
        self.communicator.start()
        self.communicator.cpanel_add_node()
        self.communicator.cpanel_add_edge(BOOTSTRAP_HOST, BOOTSTRAP_PORT, True)
        self.communicator.send(BOOTSTRAP_HOST, BOOTSTRAP_PORT, Msg.bs_new_servent)

    def quitting(self):
        self.communicator.send(BOOTSTRAP_HOST, BOOTSTRAP_PORT, Msg.bs_quit)
        self.communicator.cpanel_rm_node()

    def received_message(self, host, port, message):
        logging.info("%s:%d > %s" % (host, port, message))
        tokens = message.split(" ")
        if tokens[0] == Msg.bs_new_servent_id:
            self.id = int(tokens[1])
            return

        if "broadcast" in tokens[0]:
            new_broadcast = self.broadcast(message)
            if not new_broadcast:
                return

        while self.id == -1:
            pass

        if tokens[0] == Msg.bs_only_servent:
            self.active_jobs = {}
            self.num_nodes = 1
            self.node.id = 0
            self.communicator.cpanel_node_id(self.node.id)
            self.communicator.cpanel_rm_edge(BOOTSTRAP_HOST, BOOTSTRAP_PORT)
        elif tokens[0] == Msg.bs_contact_servent:
            h, p = helpers.extract_pair(tokens[1], str, int)
            self.communicator.cpanel_rm_edge(host, port)
            self.communicator.cpanel_add_edge(h, p, True)
            self.contact_servent(h, p)
        elif tokens[0] == Msg.my_child:
            self.communicator.cpanel_rm_edge(host, port)
            self.communicator.cpanel_add_edge(host, port, False)
            self.my_child(host, port, tokens[1])
        elif tokens[0] == Msg.active_jobs:
            self.active_jobs_message(tokens[1])
        elif tokens[0] == Msg.need_a_parent:
            self.need_a_parent(host, port)
        elif tokens[0] == Msg.broadcast_num_nodes:
            self.num_nodes = int(tokens[1])
            self.reassign_jobs()
        elif tokens[0] == Msg.connect_with:
            self.connect_with(host, port, message, tokens)
        elif tokens[0] == Msg.connect_with_me:
            self.connect_with_me(int(tokens[1]), host, port)
        elif tokens[0] == Msg.broadcast_new_job:
            # {job_id} {base_points} {ratio} {width} {height}
            job = Chaos(tokens[1], eval(tokens[2]), float(tokens[3]), int(tokens[4]), int(tokens[5]))
            self.new_job(job)
        elif tokens[0] == Msg.broadcast_show_job:
            h, p = helpers.extract_pair(tokens[2], str, int)
            self.show_job(tokens[1], h, p)
        elif tokens[0] == Msg.broadcast_remove_job:
            self.remove_job(tokens[1])
        elif tokens[0] == Msg.job_data:
            self.job_data(tokens[1], int(tokens[2]), eval(tokens[3]))
        elif tokens[0] == Msg.job_data_reassign:
            self.job_data_reassign(tokens[1], int(tokens[2]), tokens[3])
        else:
            logging.debug("Unrecognized: " + message)

    broadcasts_cache = set()

    def broadcast(self, message) -> bool:
        bc_id = message.split(" ")[-1]
        if bc_id in self.broadcasts_cache:
            return False
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
        return True

    # ------ received_message methods ------

    def contact_servent(self, host2, port2):
        self.communicator.send(host2, port2, Msg.need_a_parent)

    def need_a_parent(self, host, port):
        while self.node.id == -1:
            pass

        retry = True
        while retry:
            retry = False
            n = self.num_nodes
            with self.thread_lock:
                if n == node_tools.left_child_id(self.node.id):
                    if self.node.left_child is None:
                        # init left child
                        self.node.left_child = host, port
                        left_id = node_tools.left_child_id(self.node.id)
                        self.communicator.send(host, port, "%s %d" % (Msg.my_child, left_id))

                        # tell my left child's previous to connect with my left child
                        left_child_previous = node_tools.previous_id(left_id)
                        if left_child_previous != -1:
                            h, p = self.node.next_in_path(left_child_previous)
                            self.communicator.forward(host, port, h, p,
                                                      "%s %d %d" % (Msg.connect_with, left_child_previous, left_id))

                        jobs = ["%s;%s;%.2f;%d;%d" % (job.id, str(job.base_points).replace(" ", ""), job.ratio,
                                                      job.width, job.height) for job in self.active_jobs.values()]
                        self.communicator.send(host, port, "%s %s" % (Msg.active_jobs, "|".join(jobs)))
                    else:
                        retry = True
                elif n == node_tools.right_child_id(self.node.id):
                    if self.node.right_child is None:
                        # init right child
                        self.node.right_child = (host, port)
                        right_i = node_tools.right_child_id(self.node.id)
                        self.communicator.send(host, port, "%s %d" % (Msg.my_child, right_i))

                        # tell my left child to connect with right child
                        assert self.node.left_child is not None
                        h, p = self.node.left_child
                        self.communicator.forward(host, port, h, p, "%s %d %d" %
                                                  (Msg.connect_with, node_tools.previous_id(right_i), right_i))

                        jobs = ["%s;%s;%.2f;%d;%d" % (job.id, str(job.base_points).replace(" ", ""), job.ratio,
                                                      job.width, job.height) for job in self.active_jobs.values()]
                        self.communicator.send(host, port, "%s %s" % (Msg.active_jobs, "|".join(jobs)))
                    else:
                        retry = True
                else:
                    next_node = self.node.next_in_path(node_tools.parent_id(n))
                    if next_node is not None:
                        h, p = next_node
                        self.communicator.send(host, port, "%s %s:%d" % (Msg.bs_contact_servent, h, p))
                    else:
                        retry = True

    def my_child(self, host, port, node_id):
        with self.thread_lock:
            self.node.id = int(node_id)
            self.num_nodes = self.node.id + 1
            self.node.parent = host, port
            self.communicator.cpanel_node_id(self.node.id)

            self.bc_cnt += 1
            bc_id = "%d:%d" % (self.id, self.bc_cnt)
            message = "%s %d %s" % (Msg.broadcast_num_nodes, self.node.id + 1, bc_id)
            self.broadcast(message)

    def connect_with(self, host, port, message, tokens):
        while self.node.id == -1:
            pass

        r_id = int(tokens[1])
        if r_id == self.node.id:
            # I am the recipient
            node_id = int(tokens[2])
            if node_id == node_tools.previous_id(self.node.id):
                self.node.previous = host, port
                self.communicator.send(host, port, "%s %d" % (Msg.connect_with_me, self.node.id))
                self.communicator.cpanel_add_edge(host, port, False)
            elif node_id == node_tools.next_id(self.node.id):
                self.node.next = host, port
                self.communicator.send(host, port, "%s %d" % (Msg.connect_with_me, self.node.id))
                self.communicator.cpanel_add_edge(host, port, False)
        else:
            # forward to the recipient
            next_node = self.node.next_in_path(r_id)
            while next_node is None:
                next_node = self.node.next_in_path(r_id)
            h, p = next_node
            self.communicator.forward(host, port, h, p, message)

    def connect_with_me(self, node_id, host, port):
        while self.node.id == -1:
            pass

        if node_id == node_tools.previous_id(self.node.id):
            self.node.previous = host, port
        elif node_id == node_tools.next_id(self.node.id):
            self.node.next = host, port

    # --------- jobs ---------

    def job_worker(self):
        while self.active_jobs is None:
            time.sleep(.1)

        while True:
            time.sleep(.5)
            if self.active_job_id is not None:
                job = self.active_jobs[self.active_job_id]  # type: Chaos
                job.calculate_next()

    def active_jobs_message(self, token):
        with self.thread_lock:
            self.active_jobs = {}
            if len(token) == 0:
                return
            job_strings = token.split("|")
            for job_string in job_strings:
                # [{job_id,base_points,ratio,width,height,bc_id}]
                job_tokens = job_string.split(";")
                job = Chaos(job_tokens[0],
                            eval(job_tokens[1]),
                            float(job_tokens[2]),
                            int(job_tokens[3]),
                            int(job_tokens[4]))
                self.active_jobs[job.id] = job

    def new_job(self, job):
        while self.active_jobs is None:
            time.sleep(.1)

        with self.thread_lock:
            self.active_jobs[job.id] = job
        self.reassign_jobs()

    def remove_job(self, job_id):
        while self.active_jobs is None:
            time.sleep(.1)

        max_wait_seconds = 15
        while job_id not in self.active_jobs:
            if max_wait_seconds < 0:
                return
            time.sleep(.1)
            max_wait_seconds -= .1

        with self.thread_lock:
            if job_id == self.active_job_id:
                self.active_job_id = None
            self.active_jobs.pop(job_id)
        self.reassign_jobs()

    def reassign_jobs(self):
        while self.active_jobs is None:
            time.sleep(.1)

        with self.thread_lock:
            assigned_jobs = chaos.assign_jobs(self.active_jobs.values(), self.num_nodes)
        old_job_id = self.active_job_id
        if old_job_id is not None:
            if self.node.id not in assigned_jobs or assigned_jobs[self.node.id] != old_job_id:
                # -- I was working on something but I'm not working on that anymore --
                # new nodes on my old job
                new_nodes = [node_id for node_id, job_id in assigned_jobs.items() if job_id == old_job_id]
                if len(new_nodes) > 0:
                    node_id = random.choice(new_nodes)
                    points = None
                    with self.thread_lock:
                        if old_job_id in self.active_jobs:
                            job = self.active_jobs[old_job_id]
                            points = str(job.calculated_points).replace(" ", "")
                            job.calculated_points = []

                    if points is not None:
                        next_node = self.node.next_in_path(node_id)
                        while next_node is None:
                            next_node = self.node.next_in_path(node_id)

                        self.communicator.send(next_node[0], next_node[1],
                                               " ".join((Msg.job_data_reassign, old_job_id, str(node_id), points)))

        if self.node.id in assigned_jobs:
            with self.thread_lock:
                self.active_job_id = assigned_jobs[self.node.id]
        logging.debug("assigned_jobs: " + str(assigned_jobs))

    def show_job(self, job_id, h, p):
        while self.active_jobs is None:
            time.sleep(.1)

        if job_id == self.active_job_id:
            job = self.active_jobs[job_id]  # type: Chaos
            points = str(job.calculated_points).replace(" ", "")
            self.communicator.send(h, p, " ".join((Msg.job_data, job_id, str(self.node.id), points)))

    def job_data(self, job_id, node_id, points):
        while self.active_jobs is None:
            time.sleep(.1)

        if self.need_job_data_for == job_id:
            with self.thread_lock:
                if self.need_job_data_for == job_id:
                    self.needed_job_data.extend(points)
                    self.need_job_data_from.remove(node_id)

    def job_data_reassign(self, job_id, node_id, points_string):
        while self.active_jobs is None:
            time.sleep(.1)

        with self.thread_lock:
            if self.node.id == node_id:
                if self.active_job_id == job_id:
                    self.active_jobs[job_id].calculated_points.extend(eval(points_string))
                    return
                else:
                    with self.thread_lock:
                        assigned_jobs = chaos.assign_jobs(self.active_jobs.values(), self.num_nodes)
                    new_nodes = [a_node_id for a_node_id, a_job_id in assigned_jobs.items() if a_job_id == job_id]
                    if len(new_nodes) > 0:
                        node_id = random.choice(new_nodes)
                    else:
                        return

        next_node = self.node.next_in_path(node_id)
        while next_node is None:
            next_node = self.node.next_in_path(node_id)

        self.communicator.send(next_node[0], next_node[1],
                               " ".join((Msg.job_data_reassign, job_id, str(node_id), points_string)))

    # ------ handle user input ------

    def user_quit(self):
        pass

    def user_start_job(self, n, ratio, width, height):
        with self.thread_lock:
            self.job_cnt += 1
            job_id = "%d:%d" % (self.id, self.job_cnt)
            job = Chaos(job_id, random_points(n, width, height), ratio, width, height)
            self.bc_cnt += 1
            bc_id = "%d:%d" % (self.id, self.bc_cnt)

        print("started job %s!" % job_id)
        self.new_job(job)
        self.broadcast(job.message() + " " + bc_id)

    def user_stop_job(self, job_id):
        with self.thread_lock:
            self.bc_cnt += 1
            bc_id = "%d:%d" % (self.id, self.bc_cnt)
        self.broadcast(" ".join([Msg.broadcast_remove_job, job_id, bc_id]))
        print("stopping job %s!" % job_id)
        self.remove_job(job_id)

    def user_show_job(self, job_id):
        while self.active_jobs is None:
            time.sleep(.1)

        if job_id not in self.active_jobs:
            print("unknown id")
            return

        with self.thread_lock:
            assigned_jobs = chaos.assign_jobs(self.active_jobs.values(), self.num_nodes)
        self.need_job_data_for = job_id
        self.need_job_data_from = set([node_id for node_id, a_job_id in assigned_jobs.items() if job_id == a_job_id])
        self.needed_job_data = []

        logging.debug("need_job_data_from: " + str(self.need_job_data_from))

        with self.thread_lock:
            self.bc_cnt += 1
            bc_id = "%d:%d" % (self.id, self.bc_cnt)
        my_hp = "%s:%d" % (self.communicator.host, self.communicator.listen_port)
        msg = " ".join((Msg.broadcast_show_job, job_id, my_hp, bc_id))
        self.broadcast(msg)

        if job_id == self.active_job_id:
            points = self.active_jobs[job_id].calculated_points[:]
            self.job_data(job_id, self.node.id, points)

        max_wait_seconds = 15
        while True:
            if len(self.need_job_data_from) == 0 or max_wait_seconds < 0:
                with self.thread_lock:
                    self.need_job_data_for = None
                    self.need_job_data_from = None
                    break
            time.sleep(.5)
            max_wait_seconds -= .5

        print("showing...")
        t_job = self.active_jobs[job_id]
        job = Chaos(job_id, t_job.base_points, t_job.ratio, t_job.width, t_job.height)
        job.calculated_points = self.needed_job_data
        job.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-ho", "--host", dest="host", type=str, default=SERVENT_HOST)
    parser.add_argument("-p", "--port", dest="port", type=int, required=True)
    parser.add_argument("-l", "--log_file", dest="log_file", type=str, required=True)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=logging.DEBUG, filemode="w")
    s = Servent(args.host, args.port)

    while True:
        input_str = input("q to quit:")
        try:
            if input_str == "q":
                s.user_quit()
                break
            if "start" in input_str:
                tokens = input_str.split(" ")
                n = int(tokens[1])
                r = float(tokens[2])
                w = int(tokens[3])
                h = int(tokens[4])
                s.user_start_job(n, r, w, h)
            if "show" in input_str:
                s.user_show_job(input_str.split(" ")[1])
            if "stop" in input_str:
                s.user_stop_job(input_str.split(" ")[1])
        except Exception as e:
            logging.exception(e)

    print("Quitting...")
    s.communicator.active = False
    s.communicator.join(100)
    print("bye")


if __name__ == '__main__':
    main()
