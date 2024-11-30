#!/usr/bin/env python3

"""Awesome Project.

Run `./do -h` for a list of available tasks.
"""

import shutil
import sys
import urllib.request

sys.path.append(".doot")

import doot as do  # noqa: E402


@do.task(do.arg("-n", "--name", default="World"))
def hello(opt):
    """Say hi!"""
    do.info(f"Hello, {opt.name}!\n")


@do.task(do.arg("-r", "--ref", help="Git ref to install [main]", default="main"))
def doot__update(opt):
    """Update doot at `.doot/doot.py` to a different version."""
    res = input("\nIf you're sure you want to update, type YES\nAnswer: ")

    do.log("")

    if res.strip().lower() != "yes":
        do.log("Update cancelled. Bye!")
        sys.exit()

    url = f"https://raw.githubusercontent.com/synic/doot/{opt.ref}/doot.py"
    shutil.move(".doot/doot.py", ".doot/doot.py.bak")

    with urllib.request.urlopen(url) as res:
        with open(".doot/doot.py", "w") as h:
            h.write(res.read().decode('utf8'))

    do.success("Update complete!")
    do.log(f" -> backup created at `.doot/doot.py.bak`")
    do.log(f" -> `.doot/doot.py` updated to `{opt.ref}` version")
    do.log("")


if __name__ == "__main__":
  do.exec(name="./do", splash=sys.modules[__name__].__doc__.split("\n")[0])

