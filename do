#!/usr/bin/env python3

r"""Doot Task File.
     _             _
  __| | ___   ___ | |_
 / _` |/ _ \ / _ \| __|
| (_| | (_) | (_) | |_ _
 \__,_|\___/ \___/ \__(_)
"""

import sys


from doot import do


@do.task(allow_extra=True)
def test(_, extra):
    """Run unit tests."""
    args = ["pytest", "./t"]
    if extra:
        args.extend(extra)
    do.run(args)


@do.task(allow_extra=True)
def lint(_, extra):
    """Lint."""
    do.run("pyright", extra)


if __name__ == "__main__":
    module = sys.modules[__name__]
    splash = "\n".join(module.__doc__.split("\n")[1:-1]) if module.__doc__ else ""
    do.exec(splash=splash)
