import argparse
import inspect
import shlex
import subprocess
import sys
from typing import Any, Callable, TypeIs, override


def get_splash_from_calling_module():
    frm = inspect.stack()[2]
    mod = inspect.getmodule(frm[0])
    return (mod.__doc__ or "").split("\n")[0]


TaskFuncZeroArg = Callable[[], Any]
TaskFuncOneArg = Callable[[argparse.Namespace], Any]
TaskFuncTwoArg = Callable[[argparse.Namespace, list[str]], Any]
TaskFunc = TaskFuncZeroArg | TaskFuncOneArg | TaskFuncTwoArg


def is_zero_arg(func: TaskFunc) -> TypeIs[TaskFuncZeroArg]:
    return len(inspect.signature(func).parameters.keys()) == 0


def is_one_arg(func: TaskFunc) -> TypeIs[TaskFuncOneArg]:
    return len(inspect.signature(func).parameters.keys()) == 1


def is_two_arg(func: TaskFunc) -> TypeIs[TaskFuncTwoArg]:
    return len(inspect.signature(func).parameters.keys()) == 2


class Argument:
    """Argument for a task.

    Multiple arguments can be passed to each task. The argument constructor
    takes the same arguments as `argparse.ArgumentParser.add_argument`, see
    https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument
    for more information.
    """

    flags: tuple[str, ...]
    action: str | None
    nargs: int | None
    default: Any | None
    choices: None | list[str] | tuple[str]
    required: bool
    help: str | None
    metavar: str | None
    dest: str | None
    deprecated: bool

    def __init__(
        self,
        *flags: str,
        action: str | None = None,
        nargs: int | None = None,
        default: Any | None = None,
        choices: list[str] | tuple[str] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | None = None,
        dest: str | None = None,
        deprecated: bool = False,
    ):
        self.flags = flags
        self.action = action
        self.nargs = nargs
        self.default = default
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar
        self.dest = dest
        self.deprecated = deprecated


class MuxGroup:
    """A mutual exclusion group.

    See
    https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_mutually_exclusive_group
    for more information.
    """

    args: tuple[Argument, ...]
    required: bool

    def __init__(self, *args: Argument, required: bool = False):
        for arg in args:
            if isinstance(arg, (Group, MuxGroup)):
                raise ValueError("You cannot add groups to a mutual exclusion group")
        self.args = args
        self.required = required


class Group:
    """An argument group.

    See https://docs.python.org/3/library/argparse.html#argument-groups for
    more information.
    """

    title: str
    args: tuple[Argument | MuxGroup, ...]
    description: str | None
    argument_default: argparse._SUPPRESS_T | None
    conflict_handler: str

    def __init__(
        self,
        title: str,
        *args: Argument | MuxGroup,
        description: str | None = None,
        argument_default: argparse._SUPPRESS_T | None = None,
        conflict_handler: str = "",
    ):
        for arg in args:
            if isinstance(arg, Group):
                raise ValueError(
                    f"You cannot add the `{arg.title}` group to the group `{self.title}`"
                )

        self.args = args
        self.title = title
        self.description = description
        self.argument_default = argument_default
        self.conflict_handler = conflict_handler


class InvalidArgumentCountException(Exception):
    def __init__(self, name: str, num_args: int):
        super().__init__(
            f"task `{name}` was defined to take {num_args} "
            + "arguments, but must be defined to take 0, 1, or 3 arguments"
        )


class Task:
    name: str
    func: TaskFunc
    parser: argparse.ArgumentParser
    allow_extra: bool
    doc: str

    def __init__(
        self,
        name: str,
        func: TaskFunc,
        parser: argparse.ArgumentParser,
        allow_extra: bool = False,
        doc: str = "",
    ):
        self.allow_extra = allow_extra
        self.name = name
        self.func = func
        self.doc = doc
        self.parser = parser

    def validate_and_get_num_args(self) -> int:
        num_args = len(inspect.signature(self.func).parameters.keys())

        if num_args > 2:
            raise InvalidArgumentCountException(self.name, num_args)

        return num_args

    @property
    def short_doc(self) -> str:
        doc = (self.doc or "").split("\n")[0]
        if doc.endswith("."):
            doc = doc[:-1]
        return doc

    @override
    def __str__(self) -> str:
        return self.name

    def __call__(self, opt: argparse.Namespace, extra: list[str] | None = None) -> Any:
        if extra is None:
            extra = []

        if is_two_arg(self.func):
            return self.func(opt, extra)
        elif is_one_arg(self.func):
            return self.func(opt)
        elif is_zero_arg(self.func):
            return self.func()


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

    logfunc: Callable[[str], None]
    parser: argparse.ArgumentParser
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    tasks: dict[str, Task]

    def __init__(
        self,
        parser: None | argparse.ArgumentParser = None,
        logfunc: Callable[[str], None] = print,
    ):
        self.logfunc = logfunc

        if parser is not None:
            self.parser = parser
        else:
            self.parser = argparse.ArgumentParser(prog=sys.argv[0], add_help=False)
        self.subparsers = self.parser.add_subparsers()
        self.tasks = {}

    def task(
        self,
        *arguments: Group | Argument | MuxGroup,
        name: str | None = None,
        allow_extra: bool = False,
    ) -> Callable[[TaskFunc], Any]:
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

        def decorator(func: TaskFunc):
            task_name = name or func.__name__.replace("__", ":").replace("_", "-")
            parser = self.subparsers.add_parser(
                task_name, help=func.__doc__, description=func.__doc__
            )
            parser.set_defaults(func=func)

            for item in arguments:
                if isinstance(item, (Group, MuxGroup)):
                    if isinstance(item, Group):
                        group = parser.add_argument_group(
                            title=item.title,
                            description=item.description,
                            argument_default=item.argument_default,
                            conflict_handler=item.conflict_handler,
                        )
                    else:
                        group = parser.add_mutually_exclusive_group(
                            required=item.required
                        )

                    for arg in item.args:
                        if not isinstance(arg, Argument):
                            raise ValueError(f"Value {arg} cannot be placed in a group")
                        group.add_argument(
                            *arg.flags,
                            action=arg.action,
                            nargs=arg.nargs,
                            default=arg.default,
                            choices=arg.choices,
                            required=arg.required,
                            help=arg.help,
                            metavar=arg.metavar,
                            dest=arg.dest,
                            deprecated=arg.deprecated,
                        )
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


# export a default instance as `do`
do = TaskManager()
