import argparse
import inspect
import subprocess
import sys


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

    def __init__(self, name="./do", default_container=None, splash="", parser=None):
        self.name = name
        self.default_container = default_container
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

    def run(self, cmd, args=None, echo=True, logstatus=False):
        args = (
            " ".join([f'"{arg}"' if " " in arg else arg for arg in args])
            if args
            else ""
        )
        command = f"{cmd} {args}"
        if echo:
            self.logcmd(command)
            self.log("")

        code = subprocess.call(command, shell=True)

        if logstatus:
            self.log("")

            if code != 0:
                self.error(f"Command exited with a non-zero exit code: {code}")
            else:
                self.info("Command completed without any errors.")

        return code

    def crun(self, cmd, args=None, container=None, echo=True, logstatus=False):
        running = False
        if container is None:
            container = self.default_container
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
            self.error(
                f'The "{container}" container does not appear '
                'to be running. Try "docker-compose up -d".'
            )
            return

        return self.run(
            f"docker exec -it {container} {cmd}", args, echo=echo, logstatus=logstatus
        )

    def help(self):
        if self.splash:
            self.info(self.splash)
            self.log()

        self.log(f"Usage: {self.name} [task]\n")
        self.log("Available tasks:\n")

        for name, task in sorted(self.tasks.items(), key=lambda t: t[0]):
            self.log(f"  {name:<22} {task.short_doc}")

    def log(self, msg="", color="\033[0m"):
        print(f"{color}{msg}\033[0m")

    def logcmd(self, msg):
        self.log(f" -> {msg}", "\033[96m")

    def info(self, msg):
        self.log(msg, "\033[96m")

    def warn(self, msg):
        self.log(msg, "\033[93m")

    def error(self, msg):
        self.log(f"ERROR: {msg}", "\033[91m")

    def fatal(self, msg, status=1):
        self.error(msg)
        sys.exit(status)

    def exec(self, args=None):
        args = args or sys.argv[1:]

        for name, task in self.tasks.items():
            task.parser.prog = f"{name} {name}"

        try:
            task = self.tasks[args[0]]
            if task.passthrough:
                args = args[1:]
        except (KeyError, IndexError):
            self.help()
            sys.exit(1)

        if task.passthrough and len(sys.argv) > 1:
            opts = argparse.Namespace()
            opts.args = args
            return task(opts)

        if not args or (len(args) == 1 and args[0] == "-h"):
            self.help()
            return

        opts, extras = self.parser.parse_known_args(args)

        if extras:
            task.parser.print_help()
            sys.exit(1)

        if not opts.func:
            self.fatal(f"function not defined for task `{task}`.")

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


_instance = TaskManager()


default_exports = [
    "run",
    "crun",
    "task",
    "run",
    "log",
    "arg",
    "info",
    "warn",
    "error",
    "fatal",
]

for name in default_exports:
    globals()[name] = getattr(_instance, name)


def main(name="./do", default_container=None, splash=""):
    _instance.parser.prog = name
    _instance.name = name
    _instance.default_container = default_container
    _instance.splash = splash
    return _instance.exec()
