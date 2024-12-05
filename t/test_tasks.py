import subprocess

import pytest

import doot


@pytest.fixture
def do():
    return doot.TaskManager()


def test_task_fail_wrong_num_args(do):
    with pytest.raises(doot._InvalidArgumentCountException):

        @do.task()
        def hello_world_one(one, two, three):
            print("whoops", one, two, three)

        _ = hello_world_one

    with pytest.raises(doot._InvalidArgumentCountException):

        @do.task()
        def hello_world_two(one, two, three):
            print("whoops", one, two, three)

        _ = hello_world_two

    with pytest.raises(doot._InvalidArgumentCountException):

        @do.task()
        def hello_world_three(one, two, **kwargs):
            print("whoops", one, two, kwargs)

        _ = hello_world_three


def test_task_works_with_zero_arguments(do):
    @do.task()
    def hello():
        return "yay"

    _ = hello

    r = do.exec(["hello"])
    assert r is not None
    assert r == "yay"


def test_task_works_with_one_argument(do):
    @do.task()
    def hello(_):
        return "yay"

    _ = hello

    r = do.exec(["hello"])
    assert r is not None
    assert r == "yay"


def test_pass_arguments(do):
    @do.task(do.arg("-n", "--name"), do.arg("-d", action="store_true"))
    def hello(opt):
        return dict(name=opt.name, d=opt.d)

    _ = hello

    r = do.exec(["hello", "-n", "world"])

    assert r is not None
    assert r["name"] == "world"
    assert not r["d"]


def test_no_allow_extra_fails_on_extra_arguments(do, mocker):
    @do.task()
    def hello():
        pass

    _ = hello

    mock_stderr = mocker.patch("sys.stderr.write")
    with pytest.raises(SystemExit):
        do.exec(["hello", "-n", "world"])

    assert mock_stderr.call_count >= 1
    assert any(
        "unrecognized arguments: -n world" in args[0][0]
        for args in mock_stderr.call_args_list
    )


def test_allow_extra(do):
    @do.task(allow_extra=True)
    def hello(_, extra):
        return extra

    _ = hello

    r = do.exec(["hello", "-n", "world"])
    assert r == ["-n", "world"]


def test_convert_underscore_to_dash(do):
    assert do.tasks == {}

    @do.task(allow_extra=True)
    def hello_world_one():
        return ""

    _ = hello_world_one

    assert list(do.tasks.keys()) == ["hello-world-one"]
    assert do.tasks["hello-world-one"].func == hello_world_one


def test_convert_double_underscore_to_colon(do):
    assert do.tasks == {}

    @do.task(allow_extra=True)
    def super__hello():
        return ""

    _ = super__hello

    assert list(do.tasks.keys()) == ["super:hello"]
    assert do.tasks["super:hello"].func == super__hello


def test_convert_double_underscore_to_colon_single_underscore_to_dash(do):
    assert do.tasks == {}

    @do.task(allow_extra=True)
    def super__hello_world():
        return ""

    _ = super__hello_world

    assert list(do.tasks.keys()) == ["super:hello-world"]
    assert do.tasks["super:hello-world"].func == super__hello_world


def test_group(do):
    assert do.tasks == {}

    @do.task(
        do.arg("-n", default="Woot"),
        do.grp(
            "T-Shirt",
            do.arg("--size"),
            do.arg("--color"),
        ),
    )
    def hello(opt):
        return [opt.name, opt.size, opt.color]

    _ = hello

    parser = do.tasks["hello"].parser
    groups = parser._action_groups

    # the custom group will be the last one, after "positional arguments"
    # and "options"
    assert len(groups) == 3
    group = groups[-1]

    assert group.title == "T-Shirt"
    actions = group._group_actions

    assert len(actions) == 2

    size = actions[-2]
    color = actions[-1]

    assert size.dest == "size"
    assert color.dest == "color"


def test_mux_group(do):
    assert do.tasks == {}

    @do.task(
        do.arg("-n", default="Woot"),
        do.muxgrp(
            do.arg("--size"),
            do.arg("--color"),
        ),
    )
    def hello(opt):
        return [opt.name, opt.size, opt.color]

    _ = hello

    parser = do.tasks["hello"].parser
    groups = parser._mutually_exclusive_groups

    assert len(groups) == 1

    actions = groups[0]._group_actions

    assert len(actions) == 2

    size = actions[-2]
    color = actions[-1]

    assert size.dest == "size"
    assert color.dest == "color"


def test_args_str_extra_none(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run("ls -lh", echo=False)
    spy.assert_called_once_with(["ls", "-lh"])


def test_args_list_extra_none(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run(["ls", "-lh"], echo=False)
    spy.assert_called_once_with(["ls", "-lh"])


def test_args_str_extra_str(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run("ls -lh", "-a -w", echo=False)
    spy.assert_called_once_with(["ls", "-lh", "-a", "-w"])


def test_args_str_extra_list(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run("ls -lh", ["-a", "-w"], echo=False)
    spy.assert_called_once_with(["ls", "-lh", "-a", "-w"])


def test_args_list_extra_str(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run(["ls", "-lh"], "-a -w", echo=False)
    spy.assert_called_once_with(["ls", "-lh", "-a", "-w"])


def test_args_str_with_quote(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run('ls "-lh foo"', echo=False)
    spy.assert_called_once_with(["ls", '"-lh foo"'])


def test_args_list_extra_list(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run(["ls", "-lh"], ["-a", "-w"], echo=False)
    spy.assert_called_once_with(["ls", "-lh", "-a", "-w"])


def test_task_group_execution(do):
    @do.task(
        do.arg("-n", default="Woot"),
        do.grp(
            "T-Shirt",
            do.arg("--size"),
            do.arg("--color"),
        ),
    )
    def hello(opt):
        return [opt.n, opt.size, opt.color]

    _ = hello
    do.exec(["hello", "--size", "L", "--color", "blue"])


def test_task_mux_group_execution(do):
    @do.task(
        do.arg("-n", default="Woot"),
        do.muxgrp(
            do.arg("--size"),
            do.arg("--color"),
        ),
    )
    def hello(opt):
        return [opt.n, opt.size, opt.color]

    _ = hello
    do.exec(["hello", "--size", "L"])


def test_task_invalid_argument_type(do):
    with pytest.raises((TypeError, AttributeError)):

        @do.task(123)
        def hello():
            pass

        _ = hello


def test_task_mux_group_execution_fails_with_both_args(do):
    @do.task(
        do.arg("-n", default="Woot"),
        do.muxgrp(
            do.arg("--size"),
            do.arg("--color"),
        ),
    )
    def hello(opt):
        return [opt.n, opt.size, opt.color]

    _ = hello

    with pytest.raises(SystemExit):
        do.exec(["hello", "--size", "L", "--color", "blue"])


def test_run_with_cwd(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run("ls -lh", cwd="/tmp", echo=False)
    spy.assert_called_once_with(["ls", "-lh"], cwd="/tmp")


def test_run_with_env(do, mocker):
    spy = mocker.spy(subprocess, "call")
    env = {"TEST": "value"}
    do.run("ls -lh", env=env, echo=False)
    spy.assert_called_once_with(["ls", "-lh"], env=env)


def test_run_with_shell(do, mocker):
    spy = mocker.spy(subprocess, "call")
    do.run("ls -lh", shell=True, echo=False)
    spy.assert_called_once_with(["ls", "-lh"], shell=True)


def test_task_with_default_values(do):
    @do.task(
        do.arg("--name", default="world"),
        do.arg("--count", type=int, default=1),
    )
    def hello(opt):
        return [opt.name, opt.count]

    _ = hello

    r = do.exec(["hello"])
    assert r == ["world", 1]


def test_task_with_choices(do):
    @do.task(do.arg("--color", choices=["red", "blue", "green"]))
    def hello(opt):
        return opt.color

    _ = hello

    r = do.exec(["hello", "--color", "blue"])
    assert r == "blue"

    with pytest.raises(SystemExit):
        do.exec(["hello", "--color", "yellow"])


def test_task_with_required_arg(do):
    @do.task(do.arg("--name", required=True))
    def hello(opt):
        return opt.name

    _ = hello

    with pytest.raises(SystemExit):
        do.exec(["hello"])

    r = do.exec(["hello", "--name", "world"])
    assert r == "world"


def test_run_with_echo(do, mocker):
    spy_print = mocker.patch.object(do, "logfunc")
    spy_call = mocker.spy(subprocess, "call")
    do.run("ls -lh", echo=True)
    spy_print.assert_called_with("\x1b[96m -> ls -lh\n\x1b[0m")
    spy_call.assert_called_once_with(["ls", "-lh"])


def test_task_with_count_action(do):
    @do.task(do.arg("-v", action="count", default=0))
    def hello(opt):
        return opt.v

    _ = hello

    r = do.exec(["hello"])
    assert r == 0

    r = do.exec(["hello", "-v"])
    assert r == 1

    r = do.exec(["hello", "-vvv"])
    assert r == 3


def test_task_with_append_action(do):
    @do.task(do.arg("--item", action="append"))
    def hello(opt):
        return opt.item

    _ = hello

    r = do.exec(["hello", "--item", "a", "--item", "b"])
    assert r == ["a", "b"]


def test_run_failure(do):
    assert 1 == do.run("false")


def test_exec_unknown_task(do):
    with pytest.raises(SystemExit):
        with pytest.raises(KeyError):
            do.exec(["nonexistent"])


def test_task_with_nargs(do):
    @do.task(do.arg("--coords", nargs=2, type=int))
    def hello(opt):
        return opt.coords

    _ = hello

    r = do.exec(["hello", "--coords", "1", "2"])
    assert r == [1, 2]


def test_task_with_metavar(do):
    @do.task(do.arg("--name", metavar="NAME"))
    def hello(opt):
        return opt.name

    _ = hello

    parser = do.tasks["hello"].parser
    actions = parser._actions
    name_action = [a for a in actions if a.dest == "name"][0]
    assert name_action.metavar == "NAME"


def test_fatal(do):
    with pytest.raises(SystemExit):
        do.fatal("foo")
