import enum


class Color(enum.Enum):
    debug = "\033[96m"
    info = "\033[92m"
    warning = "\033[93m"
    error = "\033[91m"
    endc = "\033[0m"
