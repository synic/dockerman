import argparse
import inspect
import shlex
import subprocess
import sys


def get_splash_from_calling_module():
    frm = inspect.stack()[2]
    mod = inspect.getmodule(frm[0])
    return (mod.__doc__ or "").split("\n")[0]


class TaskManager:
    """Task registry and runner.

    Tasks can be registered by using the `task` decorator, like so:

    ```python
    import doot

    do = doot.TaskManager()

    @do.task(do.arg("-n", "--name", default="world"))
    def hello(opt)
        print(f"Hello, {opt.name}!")
    ```

    And then they can be executed by calling `do.exec()`
    """

    def __init__(self, parser=None, logfunc=print):
        self.logfunc = logfunc
        self.parser = parser or argparse.ArgumentParser(
            prog=sys.argv[0], add_help=False
        )
        self.subparsers = self.parser.add_subparsers()
        self.tasks = {}

    def task(self, *arguments, name=None, allow_extra=False):
        """Register a task.

        Usage:

        ```python
        import doot

        do = doot.TaskManager()

        @do.task(do.arg("-n", "--name", default="world"), allow_extra=True)
        def hello(opt, extra)
            print(f"Hello, {opt.name}!")
            print(f"Extra arguments were {extra}.")
        ```

        Args:
          arguments: One or more argument, group, or mux group.
          name: The name of the task (default is the name of the function,
            with `__` replaced with `:` and `_` replaced with `-`).
          allow_extra: By default, if arguments are passed on the command line
            that were not registered with this task, an error will be shown.
            Set this to `True` to allow extra arguments. They will be passed
            as the second parameter to the task function.

        Returns:
          A decorator for a function.
        """

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
                task_name, func, parser, allow_extra=allow_extra, doc=func.__doc__
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
        args = shlex.split(args, posix=False) if isinstance(args, str) else args
        extra = shlex.split(extra, posix=False) if isinstance(extra, str) else extra

        if extra is not None:
            args = [*args, *extra]

        if echo:
            self.log(f" -> {subprocess.list2cmdline(args)}", "\033[96m")
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
        self.logfunc(f"{color}{msg}\033[0m")

    def info(self, msg):
        self.log(msg, "\033[96m")

    def warn(self, msg):
        self.log(msg, "\033[93m")

    def success(self, msg):
        self.log(msg, "\033[92m")

    def error(self, msg):
        self.log(f"ERROR: {msg}", "\033[91m")

    def fatal(self, msg, status=1):
        self.error(msg)
        sys.exit(status)

    def exec(self, args=None, name=None, splash=get_splash_from_calling_module):
        name = name or sys.argv[0]
        splash = (splash() if callable(splash) else splash) or ""
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

        if task.allow_extra:
            opt, extra = self.parser.parse_known_args(args)
        else:
            opt, extra = self.parser.parse_args(args), []

        if not opt.func:
            self.fatal(f"function not defined for task `{task}`.")

        return task(opt, extra)


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
    def __init__(self, name, func, parser, allow_extra=False, doc=""):
        self.allow_extra = allow_extra
        self.name = name
        self.func = func
        self.num_args = self.validate_and_get_num_args()
        self.doc = doc
        self.parser = parser

    def validate_and_get_num_args(self):
        num_args = len(inspect.signature(self.func).parameters.keys())

        if num_args > 2:
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

    def __call__(self, opt, extra=None):
        if extra is None:
            extra = []

        if self.num_args == 2:
            return self.func(opt, extra)
        if self.num_args == 1:
            return self.func(opt)
        else:
            return self.func()


class Group:
    """An argument group.

    See https://docs.python.org/3/library/argparse.html#argument-groups for
    more information.
    """

    def __init__(self, title, *args, description=None, **kwargs):
        for arg in args:
            if isinstance(arg, Group):
                raise ValueError(
                    f"You cannot add the `{arg.title}` group to the group `{self.title}`"
                )

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
        for arg in args:
            if isinstance(arg, (Group, MuxGroup)):
                raise ValueError("You cannot add groups to a mutual exclusion group")

        self.args = args
        self.required = required


class InvalidArgumentCountException(Exception):
    def __init__(self, name, num_args):
        super().__init__(
            f"task `{name}` was defined to take {num_args} "
            "arguments, but must be defined to take 0, 1, or 3 arguments"
        )


# export a default instance as `do`
do = TaskManager()
