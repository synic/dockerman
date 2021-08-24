import argparse
from typing import Any, Callable, Optional

Command = Callable[[argparse.Namespace], Any]


class Option:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


class File(object):
    def __init__(self, fn: str) -> None:
        if fn.lower().endswith(".sql"):
            self.fmt = "sql"
        elif fn.lower().endswith(".json"):
            self.fmt = "json"
        else:
            raise ValueError("Invalid file import extension")
        self.fn = fn

    def __str__(self) -> None:
        return self.fn


class Config:
    def __init__(self):
        self.default_command: Optional[Command] = None
        self.default_container: Optional[str] = None
        self.prog_name = "./do"
        self.splash = ""
