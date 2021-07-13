import argparse
import enum
import functools
import os
import subprocess
import sys
from typing import Any, Callable, List, Optional, Tuple, Union

parser = argparse.ArgumentParser(prog="./manage")
subparsers = parser.add_subparsers()
parsers = {}
default_container = ""
default_command = None


class Color(enum.Enum):
    debug = "\033[96m"
    info = "\033[92m"
    warning = "\033[93m"
    error = "\033[91m"
    endc = "\033[0m"


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


def file(fn: str) -> Optional[File]:
    return File(fn) if fn else None


def command(
    options: Union[List[Option], Tuple[Option]] = (),
    passthrough: bool = False,
    default: bool = False,
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        global default_command

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        name = func.__name__.replace("_", "-")
        parser = subparsers.add_parser(name, help=func.__doc__)
        parser.set_defaults(func=func)

        opts = [options] if not isinstance(options, (list, tuple)) else options
        for option in opts:
            parser.add_argument(*option.args, **option.kwargs)

        wrapper.passthrough = passthrough
        wrapper.command_name = name

        if default:
            if default_command:
                raise ValueError("There can only be one default command.")
            default_command = wrapper

        parsers[name] = wrapper
        return wrapper

    return decorator


option = Option


def run(cmd: str, args: Optional[List[str]] = None, echo: bool = True) -> None:
    args = " ".join([f'"{arg}"' if " " in arg else arg for arg in args]) if args else ""
    command = f"{cmd} {args}"
    if echo:
        logcmd(command)
    os.system(command)


def crun(
    cmd: str, args: Optional[List[str]] = None, container: str = None, echo: bool = True
) -> None:
    running = False
    if container is None:
        container = default_container

    try:
        output = (
            subprocess.check_output(
                f"docker inspect --format {{{{.State.Running}}}} "
                f"{container}".split()
            )
            .decode("utf8")
            .strip()
        )
        running = output == "true"
    except subprocess.CalledProcessError:
        pass

    if not running:
        error(
            f'The "{container}" container does not appear '
            'to be running. Try "docker-compose up -d".'
        )
        return

    run(f"docker exec -it {container} {cmd}", args, echo=echo)


def log(msg: str, color: Color = Color.endc) -> None:
    print(f"{color.value}{msg}{Color.endc.value}")


def logcmd(msg: str) -> None:
    log(f" -> {msg}", Color.debug)


def info(msg: str) -> None:
    log(msg, Color.info)


def warning(msg: str) -> None:
    log(msg, Color.warning)


def error(msg: str) -> None:
    log(f"ERROR: {msg}", Color.error)


@command()
def help(args: Optional[List[str]]) -> None:
    """Print this help message."""
    parser.print_help(sys.stderr)


def main(prog: str = "./do") -> None:
    parser.prog = prog
    default = default_command.command_name if default_command else None
    args = sys.argv[1:]
    command = None

    try:
        func = parsers[args[0]]
        if func.passthrough:
            args = args[1:]
        command = func.command_name
    except (KeyError, IndexError):
        command = default

    if command and parsers[command].passthrough and len(sys.argv) > 1:
        parsers[command](args)
        sys.exit(0)

    if not args:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args, extras = parser.parse_known_args(args)

    if extras:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if getattr(args, "func", None):
        args.func(args)
