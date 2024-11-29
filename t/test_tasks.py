import unittest

import doot


class TestTasksManager(unittest.TestCase):
    def setUp(self):
        self.do = doot.TaskManager()

    def test_task_fail_wrong_num_args(self):
        with self.assertRaises(doot.InvalidArgumentCountException):

            @self.do.task()
            def hello_world(one, two, three):
                print("whoops", one, two, three)

            _ = hello_world

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
        @self.do.task(self.do.arg("-n", "--name"), doot.arg("-d", action="store_true"))
        def hello(opts):
            return dict(name=opts.name, d=opts.d)

        _ = hello

        r = self.do.exec(["hello", "-n", "world"])

        self.assertIsNotNone(r)

        if r is not None:
            self.assertEqual("world", r["name"])
            self.assertFalse(r["d"])

    def test_passthrough_arguments(self):
        @self.do.task(passthrough=True)
        def hello(opts):
            return opts.args

        _ = hello

        r = self.do.exec(["hello", "-n", "world"])
        self.assertEqual(r, ["-n", "world"])

    def test_convert_underscore_to_dash(self):
        self.assertEqual(self.do.tasks, {})

        @self.do.task(passthrough=True)
        def hello_world():
            return ""

        _ = hello_world

        self.assertEqual(list(self.do.tasks.keys()), ["hello-world"])
        self.assertEqual(self.do.tasks["hello-world"].func, hello_world)
