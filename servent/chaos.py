import random

import matplotlib.pyplot as plt


class Chaos:
    def __init__(self, base_points, ratio, width, height):
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


if __name__ == '__main__':
    points = [(1, 2000),
              (1000, 1),
              (2000, 2000)]
    c = Chaos(points, 0.5, 2005, 2005)
    for _ in range(5000):
        c.calculate_next()
    c.show()
