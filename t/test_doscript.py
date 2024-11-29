#!/usr/bin/env python


import sys

sys.path.insert(0, ".")

import doot as do


@do.task(
    do.arg("-n", "--name", required=True),
    do.grp(
        "Demographics",
        do.arg("--age", type=int, required=True),
        do.arg("--height", help="Height, in feet", type=float, required=True),
    ),
)
def test_group(opt):
    print(f"Name was {opt.name}")
    print(f"Age was {opt.age}")
    print(f"Height was {opt.height}")


@do.task(
    do.muxgrp(
        do.arg("--quality", action="store_true"),
        do.arg("--fast", action="store_true"),
    ),
)
def test_muxgroup(opt):
    if not opt.quality and not opt.fast:
        print("Neither fast nor quality was chosen")
        return

    if opt.quality:
        print("Quality was chosen")
    else:
        print("Fast was chosen")


@do.task(
    do.muxgrp(
        do.arg("--quality", action="store_true"),
        do.arg("--fast", action="store_true"),
        required=True,
    ),
)
def test_muxgroup_req(opt):
    if opt.quality:
        print("Quality was chosen")
    else:
        print("Fast was chosen")


@do.task(passthrough=True)
def ls(opt):
    do.run("ls", opt.args)


@do.task(passthrough=True)
def ls_list(opt):
    do.run(["ls"], opt.args)


if __name__ == "__main__":
    do.exec()
