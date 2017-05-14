import re

__host_and_port_r = re.compile("\((.*):(\d+)\)")


def extract_host_and_port(message) -> (str, int):
    groups = __host_and_port_r.match(message).groups()
    return groups[0], int(groups[1])
