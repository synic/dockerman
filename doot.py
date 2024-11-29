import argparse
import inspect
import subprocess
import sys

logfunc = print


class TaskManager:
    """Task registry and runner.

    Tasks can be registered by using the `task` decorator, like so:

    ```python
    do = TaskManager()

    @do.task(do.arg("-n", "--name", default="world"))
    def hello(opts)
        print(f"Hello, {opts.name}!")
    ```

    And then they can be executed by calling `do.exec()`
    """

    def __init__(self, name="./do", splash="", parser=None):
        self.name = name
        self.splash = splash
        self.parser = parser or argparse.ArgumentParser(prog=name, add_help=False)
        self.subparsers = self.parser.add_subparsers()
        self.tasks = {}

    def task(self, *arguments, name=None, passthrough=False):
        def decorator(func):
            task_name = name or func.__name__.replace("_", "-")
            parser = self.subparsers.add_parser(
                task_name, help=func.__doc__, description=func.__doc__
            )
            parser.set_defaults(func=func)

            args = (
                [arguments] if not isinstance(arguments, (list, tuple)) else arguments
            )

            for arg in args:
                parser.add_argument(*arg.args, **arg.kwargs)

            task = Task(
                task_name, func, parser, passthrough=passthrough, doc=func.__doc__
            )

            self.tasks[task_name] = task
            return func

        return decorator

    def arg(self, *args, **kwargs):
        return Argument(*args, **kwargs)

    def run(self, args, echo=True, **kwargs):
        display = args if isinstance(args, str) else subprocess.list2cmdline(args)
        if echo:
            log(f" -> {display}", "\033[96m")
            log("")

        return subprocess.call(args, **kwargs)

    def print_help(self):
        if self.splash:
            info(self.splash)
            log()

        log(f"Usage: {self.name} [task]\n")
        log("Available tasks:\n")

        for name, task in sorted(self.tasks.items(), key=lambda t: t[0]):
            log(f"  {name:<22} {task.short_doc}")

    def exec(self, args=None):
        args = args or sys.argv[1:]

        for name, task in self.tasks.items():
            task.parser.prog = f"{name} {name}"

        try:
            task = self.tasks[args[0]]
            if task.passthrough:
                args = args[1:]
        except (KeyError, IndexError):
            self.print_help()
            sys.exit(1)

        if task.passthrough and len(sys.argv) > 1:
            opts = argparse.Namespace()
            opts.args = args
            return task(opts)

        if not args or (len(args) == 1 and args[0] == "-h"):
            self.print_help()
            return

        opts, extras = self.parser.parse_known_args(args)

        if extras:
            task.parser.print_help()
            sys.exit(1)

        if not opts.func:
            fatal(f"function not defined for task `{task}`.")

        return task(opts)


class Argument:
    """Argument for a task.

    Multiple arguments can be passed to each task. The argument constructor
    takes the same arguments as `argparse.ArgumentParser.add_argument`, see
    https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument
    for more information.
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Task:
    def __init__(self, name, func, parser, passthrough=False, doc=""):
        self.name = name
        self.func = func
        self.num_args = self.validate_and_get_num_args()
        self.doc = doc
        self.parser = parser
        self.passthrough = passthrough

    def validate_and_get_num_args(self):
        num_args = len(inspect.signature(self.func).parameters.keys())

        if num_args > 1:
            raise InvalidArgumentCountException(self.name, num_args)

        return num_args

    @property
    def short_doc(self):
        doc = (self.doc or "").split("\n")[0]
        if doc.endswith("."):
            doc = doc[:-1]
        return doc

    def __call__(self, opts):
        if self.num_args == 1:
            return self.func(opts)
        else:
            return self.func()


class InvalidArgumentCountException(Exception):
    def __init__(self, name, num_args):
        super().__init__(
            f"task `{name}` was defined to take {num_args} "
            "arguments, but must be defined to take 0 or 1 arguments"
        )


def log(msg="", color="\033[0m"):
    logfunc(f"{color}{msg}\033[0m")


def info(msg):
    log(msg, "\033[96m")


def warn(msg):
    log(msg, "\033[93m")


def error(msg):
    log(f"ERROR: {msg}", "\033[91m")


def fatal(msg, status=1):
    error(msg)
    sys.exit(status)


_instance = TaskManager()
default_exports = ["run", "task", "run", "arg"]

for name in default_exports:
    globals()[name] = getattr(_instance, name)


def exec(name="./do", splash=""):
    _instance.parser.prog = name
    _instance.name = name
    _instance.splash = splash
    return _instance.exec()
