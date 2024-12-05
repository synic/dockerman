import argparse
import inspect
import shlex
import subprocess
import sys
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    overload,
)


def get_splash_from_calling_module() -> str:
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

    logfunc: Callable[[str], None]
    parser: argparse.ArgumentParser
    subparser: argparse._SubParsersAction
    tasks: Dict[str, "Task"]

    def __init__(
        self,
        parser: Union[argparse.ArgumentParser, None] = None,
        logfunc: Callable[[str], None] = print,
    ) -> None:
        self.logfunc = logfunc
        self.parser = parser or argparse.ArgumentParser(
            prog=sys.argv[0], add_help=False
        )
        self.subparser = self.parser.add_subparsers()
        self.tasks = {}

    def task(
        self,
        *arguments: "Argument | Group | MuxGroup",
        name: Union[str, None] = None,
        allow_extra: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a function as a command-line task.

        This decorator registers a function as a task that can be executed from the command line.
        The decorated function should accept either no arguments, one argument (the parsed options),
        or two arguments (parsed options and remaining arguments).

        Args:
            *arguments: Variable number of Argument, Group, or MuxGroup objects that define
                the command-line interface for this task.
            name: Optional custom name for the task. If not provided, the function name is used
                with underscores converted to hyphens and double underscores to colons.
            allow_extra: If True, allows additional command-line arguments after the defined ones.
                These will be passed to the task function as the second argument.

        Returns:
            A decorator function that registers the task.

        Examples:
            Basic task with arguments:
                >>> @do.task(
                ...     do.arg("-n", "--name", help="Your name"),
                ...     do.arg("--verbose", action="store_true")
                ... )
                ... def greet(opt):
                ...     if opt.verbose:
                ...         print(f"Hello, {opt.name}!")
                ...     else:
                ...         print(f"Hi {opt.name}")

            Task with a custom name:
                >>> @do.task(
                ...     do.arg("--count", type=int),
                ...     name="count-to"
                ... )
                ... def count(opt):
                ...     for i in range(opt.count):
                ...         print(i)

            Task with argument groups:
                >>> @do.task(
                ...     do.grp("input",
                ...         do.arg("--input-file"),
                ...         do.arg("--input-format")
                ...     ),
                ...     do.grp("output",
                ...         do.arg("--output-file"),
                ...         do.arg("--output-format")
                ...     )
                ... )
                ... def convert(opt):
                ...     pass

        Raises:
            InvalidArgumentCountException: If the decorated function accepts more than 2 arguments.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            task_name = name or func.__name__.replace("__", ":").replace("_", "-")
            parser = self.subparser.add_parser(
                task_name, help=func.__doc__, description=func.__doc__
            )
            parser.set_defaults(func=func)

            for item in arguments:
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
                        _: Any = group.add_argument(
                            *arg.args,
                            action=arg.action,
                            nargs=arg.nargs,
                            const=arg.const,
                            default=arg.default,
                            type=arg.type,
                            choices=arg.choices,
                            required=arg.required,
                            help=arg.help,
                            metavar=arg.metavar,
                            dest=arg.dest,
                            **arg.extra_kwargs,
                        )
                    continue
                kwargs: dict[str, Any] = {"action": item.action}

                if item.help is not None:
                    kwargs["help"] = item.help
                if item.dest is not None:
                    kwargs["dest"] = item.dest
                if item.required:
                    kwargs["required"] = item.required

                if item.action not in ("store_true", "store_false"):
                    if item.const is not None:
                        kwargs["const"] = item.const

                    if item.action not in ("store_const", "append_const"):
                        if item.nargs is not None:
                            kwargs["nargs"] = item.nargs
                        if item.default is not None:
                            kwargs["default"] = item.default
                        if item.type is not None:
                            kwargs["type"] = item.type
                        if item.choices is not None:
                            kwargs["choices"] = item.choices
                        if item.metavar is not None:
                            kwargs["metavar"] = item.metavar

                kwargs.update(item.extra_kwargs)
                _: Any = parser.add_argument(*item.args, **kwargs)

            task = Task(
                task_name, func, parser, allow_extra=allow_extra, doc=func.__doc__
            )

            self.tasks[task_name] = task
            return func

        return decorator

    def grp(
        self,
        title: str,
        *args: "Argument",
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> "Group":
        """Create an argument group for organizing related command-line arguments.

        Argument groups allow you to create logical groupings of related arguments
        in the help output. Arguments in a group are still part of the main parser
        but are displayed separately in the help message.

        Args:
            title: The title of the argument group.
            *args: Variable number of Argument objects to include in this group.
            description: Optional longer description of the argument group.
            **kwargs: Additional keyword arguments passed to argparse.ArgumentParser.add_argument_group().

        Returns:
            Group: A Group object that can be passed to the @do.task decorator.

        Examples:
            >>> @do.task(
            ...     do.grp("input options",
            ...         do.arg("--input-file", help="Input file path"),
            ...         do.arg("--format", choices=["json", "yaml"]),
            ...         description="Options for input handling"
            ...     ),
            ...     do.grp("output options",
            ...         do.arg("--output-dir", help="Output directory"),
            ...         do.arg("--compress", action="store_true")
            ...     )
            ... )
            ... def convert(opt):
            ...     pass
        """
        return Group(title, *args, description=description, **kwargs)

    def muxgrp(self, *args: "Argument", required: bool = False) -> "MuxGroup":
        """Create a mutually exclusive group of arguments.

        A mutually exclusive group ensures that only one of the arguments in the group
        can be provided at a time. If multiple arguments from the group are provided,
        an error will be raised.

        Args:
            *args: Variable number of Argument objects that are mutually exclusive.
            required: If True, one of the arguments in the group must be provided.
                     If False, the arguments are optional. Defaults to False.

        Returns:
            MuxGroup: A MuxGroup object that can be passed to the @do.task decorator.

        Examples:
            >>> @do.task(
            ...     do.muxgrp(
            ...         do.arg("--quiet", action="store_true"),
            ...         do.arg("--verbose", action="store_true"),
            ...         required=False
            ...     ),
            ...     do.muxgrp(
            ...         do.arg("--json", action="store_true"),
            ...         do.arg("--yaml", action="store_true"),
            ...         required=True
            ...     )
            ... )
            ... def process(opt):
            ...     pass

        Note:
            You cannot add groups (Group or MuxGroup) to a mutual exclusion group.
            Only individual arguments are allowed.
        """
        return MuxGroup(*args, required=required)

    @overload
    def arg(
        self,
        *name_or_flags: str,
        action: Literal["store_true", "store_false"],
        help: Optional[str] = None,
        dest: Optional[str] = None,
        required: bool = False,
        **kwargs: Any,
    ) -> "Argument": ...

    @overload
    def arg(
        self,
        *name_or_flags: str,
        action: Literal["store_const", "append_const"],
        const: Any,
        help: Union[str, None] = None,
        dest: Union[str, None] = None,
        required: bool = False,
        **kwargs: Any,
    ) -> "Argument": ...

    @overload
    def arg(
        self,
        *name_or_flags: str,
        action: Union[
            Literal["store", "append", "extend"], Type[argparse.Action], None
        ] = None,
        nargs: Union[int, Literal["?", "*", "+", "..."], None] = None,
        const: Any = None,
        default: Any = None,
        type: Optional[Callable[[str], Any]] = None,
        choices: Optional[List[Any]] = None,
        required: bool = False,
        help: Union[str, None] = None,
        metavar: Union[str, Tuple[str, ...], None] = None,
        dest: Union[str, None] = None,
        **kwargs: Any,
    ) -> "Argument": ...

    def arg(
        self,
        *name_or_flags: str,
        action: Union[
            Literal[
                "store",
                "store_true",
                "store_false",
                "store_const",
                "append",
                "append_const",
                "extend",
            ],
            Type[argparse.Action],
            None,
        ] = None,
        nargs: Union[int, Literal["?", "*", "+", "..."], None] = None,
        const: Any = None,
        default: Any = None,
        type: Union[Callable[[str], Any], None] = None,
        choices: Union[List[Any], None] = None,
        required: bool = False,
        help: Union[str, None] = None,
        metavar: Union[str, Tuple[str, ...], None] = None,
        dest: Union[str, None] = None,
        **kwargs: Any,
    ) -> "Argument":
        """Create a new command-line argument for a task.

        Args:
            name_or_flags: Either a name or a list of option strings, e.g. foo
                or -f, --foo.

            action: The basic type of action to be taken when this argument is encountered:
                - 'store' (default): Store the argument's value
                - 'store_true'/'store_false': Store True/False respectively
                - 'store_const': Store value specified by const
                - 'append': Store value in a list, can be specified multiple times
                - 'append_const': Store const value in a list
                - 'extend': Similar to append but for multiple values
                Can also be a custom Action subclass.

            nargs: Number of command-line arguments that should be consumed:
                - N (integer): Exactly N arguments
                - '?': Zero or one arguments
                - '*': Zero or more arguments
                - '+': One or more arguments
                - '...': All remaining arguments

            const: Constant value required by some action/nargs combinations,
                e.g. with action='store_const' or nargs='?'.

            default: Value produced if the argument is absent from the command
            line and if it is absent from the namespace object.

            type: Type to which the command-line argument should be converted.
                By default, str.

            choices: list
                Container of allowable values for the argument.

            required:
                Whether the argument is required or optional.

            help:
                Brief description of what the argument does.

            metavar:
                Name for the argument in usage messages.

            dest:
                Name of the attribute under which arg will be stored.
                By default, derived from the option strings.

            **kwargs:
                Additional keyword arguments for custom actions.

        Returns:
            An Argument object that can be passed to @do.task decorator.

        Example:

        ```python
        >>> @do.task(
        ...     do.arg("-n", "--name", help="Your name"),
        ...     do.arg("--verbose", action="store_true"),
        ...     do.arg("--count", type=int, default=1),
        ... )
        ... def greet(opt):
        ...     for _ in range(opt.count):
        ...         if opt.verbose:
        ...             print(f"Hello, {opt.name}!")
        ...         else:
        ...             print(f"Hi {opt.name}")
        ```
        """
        return Argument(
            *name_or_flags,
            action=action,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
            dest=dest,
            **kwargs,
        )

    def run(
        self,
        args: Union[str, List[str]],
        extra: Union[str, List[str], None] = None,
        echo: bool = True,
        **kwargs: Any,
    ) -> int:
        args_list: list[str] = (
            shlex.split(args, posix=False) if isinstance(args, str) else args
        )
        extra_list: Optional[List[str]] = (
            shlex.split(extra, posix=False) if isinstance(extra, str) else extra
        )

        if extra_list is not None:
            args_list = [*args_list, *extra_list]

        if echo:
            self.log(f" -> {subprocess.list2cmdline(args_list)}\n", "\033[96m")

        return subprocess.call(args_list, **kwargs)

    def print_help(
        self,
        name: Union[str, None] = None,
        splash: Union[str, None] = None,
        show_usage: bool = True,
    ) -> None:
        name = name or sys.argv[0]
        if splash:
            self.info(splash)
            self.log()

        if show_usage:
            self.log(f"Usage: {name} [task]\n")

        self.log("Available tasks:\n")

        for name, task in self.tasks.items():
            self.log(f" {name:<22} {task.short_doc}")

        self.log("")

    def log(self, msg: str = "", color: str = "\033[0m") -> None:
        self.logfunc(f"{color}{msg}\033[0m")

    def info(self, msg: str) -> None:
        self.log(msg, "\033[96m")

    def warn(self, msg: str) -> None:
        self.log(msg, "\033[93m")

    def success(self, msg: str) -> None:
        self.log(msg, "\033[92m")

    def error(self, msg: str) -> None:
        self.log(f"ERROR: {msg}", "\033[91m")

    def fatal(self, msg: str, status: int = 1) -> None:
        self.error(msg)
        sys.exit(status)

    def exec(
        self,
        args: Optional[List[str]] = None,
        name: Optional[str] = None,
        splash: Union[Callable[[], str], str] = get_splash_from_calling_module,
    ) -> Any:
        name = name or sys.argv[0]
        splash_str: str = (splash() if callable(splash) else splash) or ""
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

            self.print_help(name=name, splash=splash_str)
            return

        try:
            task = self.tasks[args[0]]
        except KeyError:
            self.error(f"Invalid command: {args[0]}\n")
            self.print_help(name=name, splash=None, show_usage=False)
            sys.exit(1)
        except IndexError:
            self.print_help(name=name, splash=splash_str)
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

    args: Tuple[str, ...]
    action: Union[
        Literal[
            "store",
            "store_true",
            "store_false",
            "store_const",
            "append",
            "append_const",
            "extend",
        ],
        Type[argparse.Action],
        None,
    ]
    nargs: Union[int, Literal["?", "*", "+", "..."], None]
    const: Any
    default: Any
    type: Union[Callable[[str], Any], None]
    choices: Union[List[Any], None]
    required: bool
    help: Union[str, None]
    metavar: Union[str, Tuple[str, ...], None]
    dest: Union[str, None]
    extra_kwargs: Dict[str, Any]

    @overload
    def __init__(
        self,
        *name_or_flags: str,
        action: Literal["store_true", "store_false"],
        help: Union[str, None] = None,
        dest: Union[str, None] = None,
        required: bool = False,
        **kwargs: Any,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *name_or_flags: str,
        action: Literal["store_const", "append_const"],
        const: Any,
        help: Union[str, None] = None,
        dest: Union[str, None] = None,
        required: bool = False,
        **kwargs: Any,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *name_or_flags: str,
        action: Union[
            Literal["store", "append", "extend"], Type[argparse.Action], None
        ] = None,
        nargs: Union[int, Literal["?", "*", "+", "..."], None] = None,
        const: Any = None,
        default: Any = None,
        type: Union[Callable[[str], Any], None] = None,
        choices: Union[List[Any], None] = None,
        required: bool = False,
        help: Union[str, None] = None,
        metavar: Union[str, Tuple[str, ...], None] = None,
        dest: Union[str, None] = None,
        **kwargs: Any,
    ) -> None: ...

    def __init__(
        self,
        *name_or_flags: str,
        action: Union[
            Literal[
                "store",
                "store_true",
                "store_false",
                "store_const",
                "append",
                "append_const",
                "extend",
            ],
            Type[argparse.Action],
            None,
        ] = None,
        nargs: Union[int, Literal["?", "*", "+", "..."], None] = None,
        const: Any = None,
        default: Any = None,
        type: Union[Callable[[str], Any], None] = None,
        choices: Union[List[Any], None] = None,
        required: bool = False,
        help: Union[str, None] = None,
        metavar: Union[str, Tuple[str, ...], None] = None,
        dest: Union[str, None] = None,
        **kwargs: Any,
    ) -> None:
        self.args = name_or_flags
        self.action = action
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar
        self.dest = dest
        self.extra_kwargs = kwargs


class Task:
    allow_extra: bool
    name: str
    func: Callable[..., Any]
    num_args: int
    doc: str
    parser: argparse.ArgumentParser

    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        parser: argparse.ArgumentParser,
        allow_extra: bool = False,
        doc: Optional[str] = None,
    ) -> None:
        self.allow_extra = allow_extra
        self.name = name
        self.func = func
        self.num_args = self.validate_and_get_num_args()
        self.doc = doc or ""
        self.parser = parser

    def validate_and_get_num_args(self) -> int:
        num_args = len(inspect.signature(self.func).parameters.keys())

        if num_args > 2:
            raise InvalidArgumentCountException(self.name, num_args)

        return num_args

    @property
    def short_doc(self) -> str:
        doc = self.doc.split("\n")[0]
        if doc.endswith("."):
            doc = doc[:-1]
        return doc

    def __str__(self) -> str:
        return self.name

    def __call__(
        self, opt: argparse.Namespace, extra: Union[List[str], None] = None
    ) -> Any:
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

    args: Tuple["Argument", ...]
    title: str
    description: Union[str, None]
    kwargs: Dict[str, Any]

    def __init__(
        self,
        title: str,
        *args: "Argument",
        description: Union[str, None] = None,
        **kwargs: Any,
    ) -> None:
        for arg in args:
            if isinstance(arg, Group):
                raise ValueError(
                    f"You cannot add the `{arg.title}` group to the group `{title}`"
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

    args: Tuple["Argument", ...]
    required: bool

    def __init__(self, *args: "Argument", required: bool = False) -> None:
        for arg in args:
            if isinstance(arg, (Group, MuxGroup)):
                raise ValueError("You cannot add groups to a mutual exclusion group")

        self.args = args
        self.required = required


class InvalidArgumentCountException(Exception):
    def __init__(self, name: str, num_args: int):
        super().__init__(
            f"task `{name}` was defined to take {num_args} "
            + "arguments, but must be defined to take 0, 1, or 2 arguments"
        )


# export a default instance as `do`
do: TaskManager = TaskManager()
