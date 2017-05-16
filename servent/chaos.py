import random

import matplotlib.pyplot as plt
from common.communication import Msg


class Chaos:
    def __init__(self, job_id, base_points, ratio, width, height):
        self.id = job_id
        self.base_points = base_points
        self.ratio = ratio
        self.width = width
        self.height = height
        self.calculated_points = []
        self.current_point = base_points[0]
        self.n = len(self.base_points)

    def calculate_next(self):
        i = random.randint(0, self.n - 1)
        a = self.base_points[i]
        b = self.current_point
        new_point = ((a[0] + b[0]) * self.ratio, (a[1] + b[1]) * self.ratio)
        self.current_point = new_point
        self.calculated_points.append(new_point)

    def show(self):
        plt.scatter(*zip(*self.base_points), s=20)
        plt.scatter(*zip(*self.calculated_points), s=1)
        plt.show()

    def message(self):
        return " ".join((Msg.broadcast_new_job, self.id, str(self.base_points).replace(" ", ""), str(self.ratio),
                         str(self.width), str(self.height)))


# returns dict with node_tree_id -> job_id
def assign_jobs(jobs, total_num_nodes) -> {int: str}:
    nodes_used = len(jobs)
    # every job should be assigned to at least one node
    if nodes_used > total_num_nodes:
        # if not possible, skip last job
        return assign_jobs(jobs[:-1], total_num_nodes)

    # (job_id, num_nodes, job)
    jobs = sorted([(job.id, 1, job) for job in jobs])

    i = 0
    stop_at_end = False
    while True:
        job_id, num_nodes, job = jobs[i]
        new_num_nodes = num_nodes * job.n
        if nodes_used - num_nodes + new_num_nodes <= total_num_nodes:
            jobs[i] = (job_id, new_num_nodes, job)
            nodes_used = nodes_used - num_nodes + new_num_nodes
        else:
            stop_at_end = True

        if stop_at_end and (i == len(jobs) - 1):
            break
        i = (i + 1) % len(jobs)

    i = 0
    assignees = {}
    for job_id, num_nodes, job in jobs:
        for _ in range(num_nodes):
            assignees[i] = job_id
            i += 1

    return assignees


def random_points(n, width, height):
    return [(random.randint(0, width), random.randint(0, height)) for _ in range(n)]


if __name__ == '__main__':
    c = [
        Chaos("1", random_points(7, 2005, 2005), 0.5, 2005, 2005),
        Chaos("2", random_points(5, 2005, 2005), 0.5, 2005, 2005),
        Chaos("3", random_points(3, 2005, 2005), 0.5, 2005, 2005),
        # Chaos("4", random_points(4, 2005, 2005), 0.5, 2005, 2005),
        # Chaos("5", random_points(3, 2005, 2005), 0.5, 2005, 2005),
        # Chaos("6", random_points(4, 2005, 2005), 0.5, 2005, 2005)
    ]
    xs = assign_jobs(c, 2)
    ys = [x[1] for x in xs]
    print(ys)
    print(sum(ys))
    # for _ in range(5000):
    #     c.calculate_next()
    # c.show()
