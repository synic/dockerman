import argparse
import enum
import functools
import inspect
import subprocess
import sys

parser = argparse.ArgumentParser(prog="./do", add_help=False)
subparsers = parser.add_subparsers()
tasks = {}


class Config:
    def __init__(self, name="./do", default_container=None, splash=""):
        self.name = name
        self.default_container = default_container
        self.splash = splash


config = Config()


class Option:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class File(object):
    def __init__(self, fn):
        if fn.lower().endswith(".sql"):
            self.fmt = "sql"
        elif fn.lower().endswith(".json"):
            self.fmt = "json"
        else:
            raise ValueError("Invalid file import extension")
        self.fn = fn

    def __str__(self):
        return self.fn


class Task:
    def __init__(self, name, func, parser, passthrough=False, hidden=False, doc=""):
        self.func = func
        self.doc = doc
        self.name = name
        self.parser = parser
        self.passthrough = passthrough
        self.hidden = hidden

    @property
    def short_doc(self):
        doc = (self.doc or "").split("\n")[0]
        if doc.endswith("."):
            doc = doc[:-1]
        return doc

    def __call__(self, opts):
        num_args = len(inspect.signature(self.func).parameters.keys())

        if num_args > 1:
            error("tasks must be defined take 0 or 1 arguments")
            info(f"task `{self.name}` was defined to take {num_args} arguments")
            sys.exit(1)

        if num_args == 1:
            self.func(opts)
        else:
            self.func()


class Color(enum.Enum):
    debug = "\033[96m"
    info = "\033[92m"
    warning = "\033[93m"
    error = "\033[91m"
    endc = "\033[0m"


# option aliases
opt = option = Option


def file(fn):
    return File(fn) if fn else None


def task(*options, name=None, passthrough=False, hidden=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(opts=None):
            task(opts)

        task_name = name or func.__name__.replace("_", "-")
        parser = subparsers.add_parser(
            task_name, help=func.__doc__, description=func.__doc__
        )
        parser.set_defaults(func=func)

        opts = [options] if not isinstance(options, (list, tuple)) else options

        for option in opts:
            parser.add_argument(*option.args, **option.kwargs)

        task = Task(
            task_name,
            func,
            parser,
            passthrough=passthrough,
            hidden=hidden,
            doc=func.__doc__,
        )

        tasks[task_name] = task
        return wrapper

    return decorator


# task aliases - they are officially `tasks` now, but they used to be
# commands, so alias here for backwards compatibility
cmd = command = task


def run(cmd, args=None, echo=True, logstatus=False):
    args = " ".join([f'"{arg}"' if " " in arg else arg for arg in args]) if args else ""
    command = f"{cmd} {args}"
    if echo:
        logcmd(command)
        log("")

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


@task(hidden=True)
def help():
    if config.splash:
        log(config.splash, Color.debug)
        log()

    log(f"Usage: {config.name} [task]\n")
    log("Available tasks:\n")

    for name, task in sorted(tasks.items(), key=lambda t: t[0]):
        if not task.hidden:
            log(f"  {name:<22} {task.short_doc}")


def main(name="./do", default_container=None, splash=""):
    parser.prog = name
    config.name = name
    config.default_container = default_container
    config.splash = splash
    args = sys.argv[1:]
    task = None

    for name, task in tasks.items():
        task.parser.prog = f"{name} {name}"

    try:
        task = tasks[args[0]]
        if task.passthrough:
            args = args[1:]
    except (KeyError, IndexError):
        help()
        sys.exit(1)

    if task and task.passthrough and len(sys.argv) > 1:
        options = argparse.Namespace()
        options.args = args
        task(options)
        sys.exit(0)

    if not args or (len(args) == 1 and args[0] == "-h"):
        args = ["help"]

    options, extras = parser.parse_known_args(args)

    if extras:
        task.parser.print_help()
        sys.exit(1)

    if not options.func:
        fatal(f"function not defined for task `{task}`.")

    task(options)
