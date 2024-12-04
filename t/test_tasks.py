import subprocess
import pytest

import doot


@pytest.fixture
def do():
    return doot.TaskManager()


def test_task_fail_wrong_num_args(do):
    with pytest.raises(doot.InvalidArgumentCountException):

        @do.task()
        def hello_world_one(one, two, three):
            print("whoops", one, two, three)

        _ = hello_world_one

    with pytest.raises(doot.InvalidArgumentCountException):

        @do.task()
        def hello_world_two(one, two, three):
            print("whoops", one, two, three)

        _ = hello_world_two

    with pytest.raises(doot.InvalidArgumentCountException):

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
