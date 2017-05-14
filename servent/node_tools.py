class Node:
    def __init__(self) -> None:
        super().__init__()
        self.id = -1
        self.parent = None
        self.left_child = None
        self.right_child = None
        self.next = None
        self.previous = None

    def next_in_path(self, destination) -> (str, int):
        i = self.id
        ds = []
        if self.parent is not None:
            d = dist(destination, parent_id(i))
            ds.append((d, 0, self.parent))
        if self.left_child is not None:
            d = dist(destination, left_child_id(i))
            ds.append((d, 2, self.left_child))
        if self.right_child is not None:
            d = dist(destination, right_child_id(i))
            ds.append((d, 2, self.right_child))
        if self.next is not None:
            d = dist(destination, next_id(i))
            ds.append((d, 1, self.next))
        if self.previous is not None:
            d = dist(destination, previous_id(i))
            ds.append((d, 1, self.previous))
        if len(ds) == 0:
            return None
        ds.sort()
        print(ds)
        d, preference, node = ds[0]
        return node


__dist_cache = {}


def dist(a, b):
    if a == b:
        return 0
    if (a, b) in __dist_cache:
        return __dist_cache[(a, b)]

    al = level(a)
    bl = level(b)
    if al < bl:
        d = dist(a, parent_id(b)) + 1
    elif al > bl:
        d = dist(parent_id(a), b) + 1
    else:
        d = abs(a - b)
        if d > 2:
            d = min(d, 2 + dist(parent_id(a), parent_id(b)))

    __dist_cache[(a, b)] = d
    return d


def level(a):
    lvl = 0
    num_nodes = 1
    while True:
        if num_nodes > a:
            return lvl
        num_nodes += num_nodes + 1
        lvl += 1


def parent_id(i):
    return (i - 1) // 2


def left_child_id(i):
    return i * 2 + 1


def right_child_id(i):
    return i * 2 + 2


def previous_id(i):
    j = i - 1
    return j if level(i) == level(j) else -1


def next_id(i):
    j = i + 1
    return j if level(i) == level(j) else -1
