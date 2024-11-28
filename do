#!/usr/bin/env python

import doot as do


@do.task(
    do.option("-n", "--name", help="Your name", required=True),
    name="hello",
)
def hello_task(opts):
    print(f"Oh hello, {opts.name}!")


@do.task(passthrough=True)
def ls(opts):
    do.run("ls", opts.args)


@do.task()
def die():
    do.fatal("Whoops, croaked.")


@do.task(do.option("-s", "--shell", default="bash", help="Shell to run"))
def shell(opts):
    do.run(opts.shell)


if __name__ == "__main__":
    do.main()
