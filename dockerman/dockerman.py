import argparse
import functools
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from .color import Color
from .datatypes import Command, Config, File, Option

parser = argparse.ArgumentParser(prog="./manage", add_help=False)
subparsers = parser.add_subparsers()
parsers: Dict[str, argparse.ArgumentParser] = {}
config = Config()


def option(*args: Any, **kwargs: Any) -> Option:
    return Option(*args, **kwargs)


def file(fn: str) -> Optional[File]:
    return File(fn) if fn else None


def command(
    options: Union[List[Option], Tuple[Option]] = (),
    passthrough: bool = False,
    default: bool = False,
    hidden: bool = False,
):
    def decorator(func: Command) -> Command:
        @functools.wraps(func)
        def wrapper(opts: argparse.Namespace, args: Optional[List[str]]) -> Any:
            return func(opts=opts, args=args)

        name = func.__name__.replace("_", "-")
        parser = subparsers.add_parser(name, help=func.__doc__)
        parser.set_defaults(func=func)

        opts = [options] if not isinstance(options, (list, tuple)) else options
        for option in opts:
            parser.add_argument(*option.args, **option.kwargs)

        wrapper.passthrough = passthrough
        wrapper.command_name = name
        wrapper.hidden = hidden

        if default:
            if config.default_command:
                raise ValueError("There can only be one default command.")
            config.default_command = wrapper

        parsers[name] = wrapper
        return wrapper

    return decorator


def run(
    cmd: str,
    args: Optional[List[str]] = None,
    echo: bool = True,
    logstatus: bool = False,
) -> None:
    args = " ".join([f'"{arg}"' if " " in arg else arg for arg in args]) if args else ""
    command = f"{cmd} {args}"
    if echo:
        logcmd(command)

    code = subprocess.call(command, shell=True)

    if logstatus:
        log("")

        if code != 0:
            error(f"Command exited with a non-zero exit code: {code}")
        else:
            info("Command completed without any errors.")
    return code


def crun(
    cmd: str,
    args: Optional[List[str]] = None,
    container: str = None,
    echo: bool = True,
    logstatus: bool = False,
) -> None:
    running = False
    if container is None:
        container = config.default_container
        if not container:
            raise AttributeError(
                "Default container is not set, so you must pass a container name"
            )

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

    return run(
        f"docker exec -it {container} {cmd}", args, echo=echo, logstatus=logstatus
    )


def log(msg: str = "", color: Color = Color.endc) -> None:
    print(f"{color.value}{msg}{Color.endc.value}")


def logcmd(msg: str) -> None:
    log(f" -> {msg}", Color.debug)


def info(msg: str) -> None:
    log(msg, Color.info)


def warning(msg: str) -> None:
    log(msg, Color.warning)


def error(msg: str) -> None:
    log(f"ERROR: {msg}", Color.error)


@command(hidden=True)
def help(opts: argparse.Namespace, args: Optional[List[str]]) -> None:
    if config.splash:
        log(config.splash, Color.debug)
        log()

    log(f"Usage: {config.prog_name} [command]\n")
    log("Available commands:\n")

    for name, func in sorted(parsers.items(), key=lambda x: x[0]):
        if not func.hidden:
            log(f"  {name:<22} {func.__doc__}")


def main(
    prog_name: str = "./do", default_container: Optional[str] = None, splash: str = ""
) -> None:
    parser.prog = prog_name
    config.prog_name = prog_name
    config.default_container = default_container
    config.splash = splash
    default = config.default_command.command_name if config.default_command else None
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
        parsers[command](opts=argparse.Namespace(), args=args)
        sys.exit(0)

    if not args:
        help(None, None)
        sys.exit(1)

    options, extras = parser.parse_known_args(args)

    if extras:
        help(None, None)
        sys.exit(1)

    if getattr(options, "func", None):
        options.func(opts=options, args=extras)
