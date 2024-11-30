#!/usr/bin/env python

r"""Doot Task File.
     _             _
  __| | ___   ___ | |_
 / _` |/ _ \ / _ \| __|
| (_| | (_) | (_) | |_ _
 \__,_|\___/ \___/ \__(_)
"""

import sys
import unittest

import doot as do


@do.task()
def test():
    """Run unit tests."""
    suite = unittest.TestLoader().discover("./t")
    runner = unittest.TextTestRunner()
    runner.run(suite)


@do.task()
def lint():
    """Lint."""
    do.run("pyright doot.py")


if __name__ == "__main__":
    module = sys.modules[__name__]
    splash = "\n".join(module.__doc__.split("\n")[1:-1])
    do.exec(splash=splash)
