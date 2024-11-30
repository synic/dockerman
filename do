#!/usr/bin/env python3

r"""Doot Task File.
     _             _
  __| | ___   ___ | |_
 / _` |/ _ \ / _ \| __|
| (_| | (_) | (_) | |_ _
 \__,_|\___/ \___/ \__(_)
"""

import sys
import unittest

from doot import do


@do.task(passthrough=True)
def test(opt):
    """Run unit tests."""
    suite = unittest.TestLoader().discover("./t")

    if opt.args:
        tests = []
        for arg in opt.args:
            test = unittest.TestLoader().loadTestsFromName(arg)
            tests.append(test)
        suite = unittest.TestSuite(tests)

    runner = unittest.TextTestRunner()
    runner.run(suite)


@do.task(passthrough=True)
def lint(opt):
    """Lint."""
    do.run("pyright", opt.args)


if __name__ == "__main__":
    module = sys.modules[__name__]
    splash = "\n".join(module.__doc__.split("\n")[1:-1])
    do.exec(splash=splash)
