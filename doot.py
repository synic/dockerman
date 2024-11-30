import argparse
import inspect
import re
import subprocess
import sys

logfunc = print


class TaskManager:
    """Task registry and runner.

    Tasks can be registered by using the `task` decorator, like so:

    ```python
    import doot

    do = doot.TaskManager()

    @do.task(doot.arg("-n", "--name", default="world"))
    def hello(opts)
        print(f"Hello, {opts.name}!")
    ```

    And then they can be executed by calling `do.exec()`
    """

    exports = "run, task, arg, grp, muxgrp, log, warn, info, error, fatal, exec"

    def __init__(self, parser=None):
        self.parser = parser or argparse.ArgumentParser(
            prog=sys.argv[0], add_help=False
        )
        self.subparsers = self.parser.add_subparsers()
        self.tasks = {}

    def task(self, *arguments, name=None, passthrough=False):
        def decorator(func):
            task_name = name or func.__name__.replace("__", ":").replace("_", "-")
            parser = self.subparsers.add_parser(
                task_name, help=func.__doc__, description=func.__doc__
            )
            parser.set_defaults(func=func)

            items = (
                [arguments] if not isinstance(arguments, (list, tuple)) else arguments
            )

            for item in items:
                if isinstance(item, (Group, MuxGroup)):
                    if isinstance(item, Group):
                        group = parser.add_argument_group(
                            title=item.title,
                            description=item.description,
                            **item.kwargs,
                        )
                    else:
                        group = parser.add_mutually_exclusive_group(
                            required=item.required
                        )

                    for arg in item.args:
                        if not isinstance(arg, Argument):
                            raise ValueError(f"Value {arg} cannot be placed in a group")
                        group.add_argument(*arg.args, **arg.kwargs)
                else:
                    parser.add_argument(*item.args, **item.kwargs)

            task = Task(
                task_name, func, parser, passthrough=passthrough, doc=func.__doc__
            )

            self.tasks[task_name] = task
            return func

        return decorator

    def grp(self, title, *args, description=None, **kwargs):
        return Group(title, *args, description=description, **kwargs)

    def muxgrp(self, *args, required=False):
        return MuxGroup(*args, required=required)

    def arg(self, *args, **kwargs):
        return Argument(*args, **kwargs)

    def run(self, args, extra=None, echo=True, **kwargs):
        if isinstance(extra, list):
            args = [args, *extra] if isinstance(args, str) else [*args, *extra]

        display = args if isinstance(args, str) else subprocess.list2cmdline(args)

        if echo:
            self.log(f" -> {display}", "\033[96m")
            self.log("")

        return subprocess.call(args, **kwargs)

    def print_help(self, name=None, splash=None, show_usage=True):
        name = name or sys.argv[0]
        if splash:
            self.info(splash)
            self.log()

        if show_usage:
            self.log(f"Usage: {name} [task]\n")

        self.log("Available tasks:\n")

        for name, task in self.tasks.items():
            self.log(f"  {name:<22} {task.short_doc}")

        self.log("")

    def log(self, msg="", color="\033[0m"):
        logfunc(f"{color}{msg}\033[0m")

    def info(self, msg):
        self.log(msg, "\033[96m")

    def warn(self, msg):
        self.log(msg, "\033[93m")

    def error(self, msg):
        self.log(f"ERROR: {msg}", "\033[91m")

    def fatal(self, msg, status=1):
        self.error(msg)
        sys.exit(status)

    def exec(self, args=None, name=None, splash=None):
        name = name or sys.argv[0]
        splash = splash or ""
        args = args or sys.argv[1:]

        for task_name, task in self.tasks.items():
            task.parser.prog = f"{name} {task_name}"

        if not args or (len(args) >= 1 and args[0] in ("-h", "help")):
            if len(args) > 1:
                try:
                    task = self.tasks[args[1]]
                    task.parser.print_help()
                    return
                except KeyError:
                    pass

            self.print_help(name=name, splash=splash)
            return

        try:
            task = self.tasks[args[0]]
        except KeyError:
            self.error(f"Invalid command: {args[0]}\n")
            self.print_help(name=name, splash=None, show_usage=False)
            sys.exit(1)
        except IndexError:
            self.print_help(name=name, splash=splash)
            sys.exit(1)

        if task.passthrough:
            opts = argparse.Namespace()
            opts.args = args[1:]
            return task(opts)

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

    def __str__(self):
        return self.name

    def __call__(self, opts):
        if self.num_args == 1:
            return self.func(opts)
        else:
            return self.func()


class Group:
    """An argument group.

    See https://docs.python.org/3/library/argparse.html#argument-groups for
    more information.
    """

    def __init__(self, title, *args, description=None, **kwargs):
        self.args = args
        self.title = title
        self.description = description
        self.kwargs = kwargs


class MuxGroup:
    """A mutual exclusion group.

    See
    https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_mutually_exclusive_group
    for more information.
    """

    def __init__(self, *args, required=False):
        self.args = args
        self.required = required


class InvalidArgumentCountException(Exception):
    def __init__(self, name, num_args):
        super().__init__(
            f"task `{name}` was defined to take {num_args} "
            "arguments, but must be defined to take 0 or 1 arguments"
        )


do = TaskManager()
for field in re.split(r",\s+?", TaskManager.exports):
    globals()[field] = getattr(do, field)
