import argparse
import functools
import inspect
import subprocess
import sys

from .color import Color
from .datatypes import Config, File, Option

parser = argparse.ArgumentParser(prog="./manage", add_help=False)
subparsers = parser.add_subparsers()
tasks = {}
config = Config()


def option(*args, **kwargs):
    return Option(*args, **kwargs)


opt = option


def file(fn):
    return File(fn) if fn else None


def task(*options, passthrough=False, hidden=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(opts=None):
            call_task_func(func, opts)

        name = func.__name__.replace("_", "-")
        func.task_name = name
        parser = subparsers.add_parser(
            name, help=func.__doc__, description=func.__doc__
        )
        parser.set_defaults(func=func)

        opts = [options] if not isinstance(options, (list, tuple)) else options

        for option in opts:
            parser.add_argument(*option.args, **option.kwargs)

        wrapper.parser = parser
        wrapper.passthrough = passthrough
        wrapper.task_name = name
        wrapper.hidden = hidden

        tasks[name] = wrapper
        return wrapper

    return decorator


cmd = command = task


def run(cmd, args=None, echo=True, logstatus=False):
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


def crun(cmd, args=None, container=None, echo=True, logstatus=False):
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


def log(msg="", color=Color.endc):
    print(f"{color.value}{msg}{Color.endc.value}")


def logcmd(msg):
    log(f" -> {msg}", Color.debug)


def info(msg):
    log(msg, Color.info)


def warning(msg):
    log(msg, Color.warning)


warn = warning


def error(msg):
    log(f"ERROR: {msg}", Color.error)


def fatal(msg, status=1):
    error(msg)
    sys.exit(status)


def normalize_doc(doc):
    doc = (doc or "").split("\n")[0]
    if doc.endswith("."):
        doc = doc[:-1]
    return doc


@task(hidden=True)
def help():
    if config.splash:
        log(config.splash, Color.debug)
        log()

    log(f"Usage: {config.prog_name} [task]\n")
    log("Available tasks:\n")

    for name, func in sorted(tasks.items(), key=lambda x: x[0]):
        if not func.hidden:
            log(f"  {name:<22} {normalize_doc(func.__doc__)}")


def call_task_func(func, opts):
    num_args = len(inspect.signature(func).parameters.keys())

    if num_args > 1:
        error("tasks must be defined take 0 or 1 arguments")
        info(f"task `{func.task_name}` was defined to take {num_args} arguments")
        sys.exit(1)

    if num_args == 1:
        func(opts)
    else:
        func()


def main(prog_name="./do", default_container=None, splash=""):
    parser.prog = prog_name
    config.prog_name = prog_name
    config.default_container = default_container
    config.splash = splash
    args = sys.argv[1:]
    task = None

    for name, func in tasks.items():
        func.parser.prog = f"{prog_name} {name}"

    try:
        func = tasks[args[0]]
        if func.passthrough:
            args = args[1:]
        task = func.task_name
    except (KeyError, IndexError):
        help()
        sys.exit(1)

    if task and tasks[task].passthrough and len(sys.argv) > 1:
        options = argparse.Namespace()
        options.args = args
        tasks[task](options)
        sys.exit(0)

    if not args or (len(args) == 1 and args[0] == "-h"):
        args = ["help"]

    options, extras = parser.parse_known_args(args)

    if extras:
        tasks[task].parser.print_help()
        sys.exit(1)

    if not options.func:
        fatal(f"function not defined for task `{task}`.")

    call_task_func(options.func, options)
