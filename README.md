         _             _
      __| | ___   ___ | |_
     / _` |/ _ \ / _ \| __|
    | (_| | (_) | (_) | |_ _
     \__,_|\___/ \___/ \__(_)

# Simple Zero Dependency Task Runner

This is a simple, zero dependency (except Python 3, which comes installed on
most *nix operating systems) task runner. Similar to `make`, but meant to be
used for non-C style projects.

Python is ideal for this sort of thing, because it has a pretty comprehensive
standard library; where most things you might need are built right in. However,
if you have more complex needs, any python library can be used as a part of
your tasks.

## Installation

There are 3 ways to install doot:

### Zero Install (recommended)

I prefer this method, as doing it this way means your coworkers don't have to
install anything etra to get it working (assuing they have Python installed,
which is usually done by default on Mac and most Linux distros).

In the repository you want to use this in, run the following:

```bash
$ mkdir -p lib
$ git submodule add https://github.com/synic/doot lib/doot
```

Then, at the top of your `do` script, before the doot import, you can add
the following:

```python
if not os.path.isfile("./lib/doot/doot/__init__.py"):
    print("`doot` not found; run `git submodule update --init`")
    sys.exit(1)

sys.path.append("./lib/doot")
```

### Install as a Library

Alternatively, you can install it as a library:

```bash
$ pip install git+https://github.com/synic/doot
```

### Copy `doot.py` to Your Repo

You can also just copy `doot.py` into your repository somewhere and include it
from there.

## Getting Started

In your project root directory, create a file (I usually call it `do`, but it
can be anything you want):

```python

#!/usr/bin/env python

import os

import doot as do

@do.task(passthrough=True)
def bash(opts):
    """Bash shell on the web container."""
    do.run("docker exec -it api bash", opts.args)


@do.task()
def start():
    """Start all services."""
    do.run("docker-compose up -d")


@do.task()
def stop():
    """Stop all services."""
    do.run("docker-compose stop")


@do.task()
def dbshell():
    """Execute a database shell."""
    do.run("docker exec -it database psql -U myuser mydatabase")


@do.task()
def shell():
    """Open a django shell on the web container."""
    do.run("docker exec -it api django-admin shell")


@do.task(passthrough=True)
def manage(opts):
    """Run a django management command."""
    do.run("docker exec -it api django-admin", opts.args)


@do.task(
    do.arg("-n", "--name", help="Container name", required=True),
    do.arg("-d", "--detach", help="Detach when running `up`", action="store_true"),
)
def reset_container(opts):
    """Reset a container."""
    do.run(f"docker-compose stop {opts.name}")
    do.run(f"docker-compose rm {opts.name}")

    extra = "-d" if opts.detach else ""
    do.run(f"docker-compose up {extra}")


if __name__ == "__main__":
    do.exec()
```

With this setup, you can run tasks like `./do manage`, `./do shell`, etc.

Running `./do -h` will show output like this:

```
Usage: ./do [task]

Available tasks:

  bash                   Bash shell on the web container
  dbshell                Execute a database shell
  manage                 Run a django management command
  reset-container        Reset a container
  shell                  Open a django shell on the web container
  start                  Start all services
  stop                   Stop all services
```

### Complex Example

To see a more complex example, look [here](docs/complex_dootfile_example.md)

## Doot Functions

### `doot.task`

This is a decorator that turns a function into a task. The task will have
the same name as the function it decorates (changing `_` to `-`), and the
docstring will be the documentation that appears when you type `./do help` or
`./do help [task]`. All underscores will be converted to hyphens in the
resulting task name.

If you specify `passthrough=True`, all extra command line arguments can be
passed to any `doot.run` statements executed within the function
(this is the purpose of the task function receiving the `opts` parameter,
and passing `opts.args` parameter to `doot.run`).

For example, if you'd like to run Django management commands in a docker
container by just running `./do manage [cmd]`:

```python
@doot.task(passthrough=True)
def manage(opts):
    """Run Django management commands."""
    doot.run("docker exec -it api django-admin", opts.args)
```

Then when you run something like:

```bash
$ ./do manage makemigrations --name add_user_is_active_field accounts
```

The `makemigrations --name add_user_is_active_field accounts` will be passed
through to `django-admin` on the container.

### `doot.run`

This runs a command on the host. Things like
`doot.run('docker network add test')`, or `doot.run(["docker", "ps", "-q"])`

The first argument of `doot.run`, `args`, and any extra **kwargs are passed
directly to `subprocess.call`. If you have more complex needs, you can use the
`subprocess` module directly; the `doot.run` function is just there for
convenience.

### `doot.arg`

You can pass one or more `doot.arg` arguments to the `doot.task` decorator.
These will set up arguments for your task, using the `argparse` module. They
are passed directly to `parser.add_argument`, so they have the same parameters.
See https://docs.python.org/3/library/argparse.html#the-add-argument-method for
more information.

An example:

```python

@doot.task(doot.arg("--name", dest="name", help="Your name"))
def hello(opts):
    print(f"Hello, {opts.name}!")
```

### `doot.log`, `doot.info`, `doot.warn`, `doot.error`

These are logging statements. Each one has it's own color indicative of the
type of message you want to show. For example:

### `doot.fatal`

`doot.fatal(msg)` will call `doot.error(msg)` and then `sys.exit(1)` (you can
specify the exit code by passing `status`, the default is `1`).

```python
@doot.task(doot.arg("--name", required=True))
def hello(opts):
    if opts.name.lower() in ("tyler", "steve", "james"):
        doot.fatal(f"Sorry, your name cannot be {opts.name}. Get a new one.")
    print(f"Hello, {opts.name}!")
```

## Acknowledgements

This project was named after our beloved Doots. She will be missed.

![Doots](docs/images/thebestdoots.jpg)
