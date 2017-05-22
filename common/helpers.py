import re
from typing import Any

__host_and_port_r = re.compile("(.*):(.*)")


def extract_pair(string, map_first, map_second) -> (Any, Any):
    groups = __host_and_port_r.match(string).groups()
    return map_first(groups[0]), map_second(groups[1])
