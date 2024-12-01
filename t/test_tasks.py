import unittest
from unittest import mock

import doot


class TestTasksManager(unittest.TestCase):
    def setUp(self):
        self.do = doot.TaskManager()

    def test_task_fail_wrong_num_args(self):
        with self.assertRaises(doot.InvalidArgumentCountException):

            @self.do.task()
            def hello_world_one(one, two, three):
                print("whoops", one, two, three)

            _ = hello_world_one

        with self.assertRaises(doot.InvalidArgumentCountException):

            @self.do.task()
            def hello_world_two(one, two, three):
                print("whoops", one, two, three)

            _ = hello_world_two

        with self.assertRaises(doot.InvalidArgumentCountException):

            @self.do.task()
            def hello_world_three(one, two, **kwargs):
                print("whoops", one, two, kwargs)

            _ = hello_world_three

    def test_task_works_with_zero_arguments(self):
        @self.do.task()
        def hello():
            return "yay"

        _ = hello

        r = self.do.exec(["hello"])
        self.assertIsNotNone(r)
        self.assertEqual("yay", r)

    def test_task_works_with_one_argument(self):
        @self.do.task()
        def hello(_):
            return "yay"

        _ = hello

        r = self.do.exec(["hello"])
        self.assertIsNotNone(r)
        self.assertEqual("yay", r)

    def test_pass_arguments(self):
        @self.do.task(
            self.do.arg("-n", "--name"), self.do.arg("-d", action="store_true")
        )
        def hello(opt):
            return dict(name=opt.name, d=opt.d)

        _ = hello

        r = self.do.exec(["hello", "-n", "world"])

        self.assertIsNotNone(r)

        if r is not None:
            self.assertEqual("world", r["name"])
            self.assertFalse(r["d"])

    def test_no_allow_extra_fails_on_extra_arguments(self):
        @self.do.task()
        def hello():
            pass

        _ = hello

        with mock.patch("sys.stderr.write") as out:
            with self.assertRaises(SystemExit):
                self.do.exec(["hello", "-n", "world"])
        self.assertEqual(2, len(out.call_args_list))
        call = out.call_args_list[1]
        self.assertIn("unrecognized arguments: -n world", call.args[0])

    def test_allow_extra(self):
        @self.do.task(allow_extra=True)
        def hello(_, extra):
            return extra

        _ = hello

        r = self.do.exec(["hello", "-n", "world"])
        self.assertEqual(r, ["-n", "world"])

    def test_convert_underscore_to_dash(self):
        self.assertEqual(self.do.tasks, {})

        @self.do.task(allow_extra=True)
        def hello_world_one():
            return ""

        _ = hello_world_one

        self.assertEqual(list(self.do.tasks.keys()), ["hello-world-one"])
        self.assertEqual(self.do.tasks["hello-world-one"].func, hello_world_one)

    def test_convert_double_underscore_to_colon(self):
        self.assertEqual(self.do.tasks, {})

        @self.do.task(allow_extra=True)
        def super__hello():
            return ""

        _ = super__hello

        self.assertEqual(list(self.do.tasks.keys()), ["super:hello"])
        self.assertEqual(self.do.tasks["super:hello"].func, super__hello)

    def test_convert_double_underscore_to_colon_single_underscore_to_dash(self):
        self.assertEqual(self.do.tasks, {})

        @self.do.task(allow_extra=True)
        def super__hello_world():
            return ""

        _ = super__hello_world

        self.assertEqual(list(self.do.tasks.keys()), ["super:hello-world"])
        self.assertEqual(self.do.tasks["super:hello-world"].func, super__hello_world)

    def test_group(self):
        self.assertEqual(self.do.tasks, {})

        @self.do.task(
            self.do.arg("-n", default="Woot"),
            self.do.grp(
                "T-Shirt",
                self.do.arg("--size"),
                self.do.arg("--color"),
            ),
        )
        def hello(opt):
            return [opt.name, opt.size, opt.color]

        _ = hello

        parser = self.do.tasks["hello"].parser
        groups = parser._action_groups

        # the custom group will be the last one, afer "positional arguments"
        # and "options"
        self.assertEqual(len(groups), 3)
        group = groups[-1]

        self.assertEqual("T-Shirt", group.title)
        actions = group._group_actions

        self.assertEqual(len(actions), 2)

        size = actions[-2]
        color = actions[-1]

        self.assertEqual(size.dest, "size")
        self.assertEqual(color.dest, "color")

    def test_mux_group(self):
        self.assertEqual(self.do.tasks, {})

        @self.do.task(
            self.do.arg("-n", default="Woot"),
            self.do.muxgrp(
                self.do.arg("--size"),
                self.do.arg("--color"),
            ),
        )
        def hello(opt):
            return [opt.name, opt.size, opt.color]

        _ = hello

        parser = self.do.tasks["hello"].parser
        groups = parser._mutually_exclusive_groups

        self.assertEqual(len(groups), 1)

        actions = groups[0]._group_actions

        self.assertEqual(len(actions), 2)

        size = actions[-2]
        color = actions[-1]

        self.assertEqual(size.dest, "size")
        self.assertEqual(color.dest, "color")

    def test_args_str_extra_none(self):
        with mock.patch("subprocess.call") as call:
            self.do.run("ls -lh", echo=False)
            call.assert_called_once_with(["ls", "-lh"])

    def test_args_list_extra_none(self):
        with mock.patch("subprocess.call") as call:
            self.do.run(["ls", "-lh"], echo=False)
            call.assert_called_once_with(["ls", "-lh"])

    def test_args_str_extra_str(self):
        with mock.patch("subprocess.call") as call:
            self.do.run("ls -lh", "-a -w", echo=False)
            call.assert_called_once_with(["ls", "-lh", "-a", "-w"])

    def test_args_str_extra_list(self):
        with mock.patch("subprocess.call") as call:
            self.do.run("ls -lh", ["-a", "-w"], echo=False)
            call.assert_called_once_with(["ls", "-lh", "-a", "-w"])

    def test_args_list_extra_str(self):
        with mock.patch("subprocess.call") as call:
            self.do.run(["ls", "-lh"], "-a -w", echo=False)
            call.assert_called_once_with(["ls", "-lh", "-a", "-w"])

    def test_args_str_with_quote(self):
        with mock.patch("subprocess.call") as call:
            self.do.run('ls "-lh foo"', echo=False)
            call.assert_called_once_with(["ls", '"-lh foo"'])
