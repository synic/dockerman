# Simple Zero Dependency Task Runner

This is a simple, zero dependency (except Python 3, which comes installed on
most *nix operating systems) task runner. Similar to `make`, but meant to be
used for non-C style projects. Comes out of the box with simple docker support.

## Installation

```bash
$ pip install git+https://github.com/synic/doot
```

Or, you can use the [Zero Install](#zero-install) option as described below.

## Getting Started

In your project root directory, create a file (I usually call it `do`, but it
can be anything you want):

```python

#!/usr/bin/env python

import os

import doot as do

@do.command(passthrough=True)
def bash(args):
    """Bash shell on the web container."""
    do.crun("bash", args)


@do.command()
def start():
    """Start all services."""
    do.run("docker-compose up -d")


@do.command()
def stop():
    """Stop all services."""
    do.run("docker-compose stop")


@do.command()
def dbshell():
    """Execute a database shell."""
    do.crun("psql -U myuser mydatabase", container="database")


@do.command()
def shell():
    """Open a django shell on the web container."""
    do.crun("django-admin shell", args)


@do.command(passthrough=True)
def manage(args):
    """Run a django management command."""
    do.crun("django-admin", args)


@do.command(
    do.option('--name', help='Container name'),
)
def reset_container(args):
    """Reset a container."""
    do.run(f"docker-compose stop {args.name}")
    do.run(f"docker-compose rm {args.name}")
    do.run("docker-compose up -d")


if __name__ == "__main__":
    do.main(default_container="web")
```

With this setup, you can run commands like `./do help`, `./do shell`, etc.

Running `./do -h` will show output like this:

```
Usage: ./do [command]

Available commands:

  bash                   Bash shell on the web container
  dbshell                Execute a database shell
  manage                 Run a django management command
  reset-container        Reset a container
  shell                  Open a django shell on the web container
  start                  Start all services
  stop                   Stop all services
```

## Docker support

When using `doot`, the `doot.run` function runs a command locally. You can use
the `doot.crun` function to run a command on a docker container, like so:

```python
@do.command(passthrough=True)
def manage(args):
    do.crun("django-admin shell", container="api", args)
```

You can set up a default container by passing `default_container` to `doot.main`,
in which case, if you do not pass `container` to `doot.crun`, the default
container will be used.

## Zero Install Option

On Mac and Linux, you can set this up to "just work" without any extra
installation (assuming python is installed, which it usually is).

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

## Doot Functions

### `doot.command`

This is a decorator that turns a function into a command. The command will have
the same name as the function it decorates, and the docstring will be the
documentation that appears when you type `./do help` or `./do help [command]`.
All underscores will be converted to hyphens in the resulting command name.

If you specify `passthrough=True`, all extra command line arguments will be
passed to any `doot.crun` or `doot.run` statements executed within the function
(this is the purpose of the command function receiving the `args` parameter,
and passing that same `args` parameter to `doot.crun` and `doot.run`).

For example, if you'd like to run Django management commands in the web
container:

```python
@doot.command(passthrough=True)
def manage(args):
    """Run Django management commands."""
    doot.crun("django-admin", args)
```

Then when you run something like:

```bash
$ ./do manage makemigrations --name add_user_is_active_field accounts
```

The `makemigrations --name add_user_is_active_field accounts` will be passed
through to `django-admin` on the container.

### `doot.run`

This runs a command on the host. Things like
`doot.run('docker network add test')` are typical.

### `doot.crun`

This runs a command in a docker container. Passing `container="web"` will tell
it to run on the "web" container. If you do not pass `container`, it will use
the container specified with `default_container` passed to the `doot.main`
function.

### `doot.option`

You can pass one or more `doot.option` arguments to the `doot.command` decorator.
These will set up argument options for your command, using the `argparse`
module. They are passed directly to `parser.add_argument`, so they have the
same parameters.

An example:

```python

@doot.command(@doot.option("--name", dest="name", help="Your name"))
def hello(args):
    print(f"Hello, {args.name}!")
```

### `doot.log`, `doot.info`, `doot.warning`, `doot.error`

These are logging statements. Each one has it's own color indicative of the
type of message you want to show. For example:

### `doot.fatal`

`doot.fatal(msg)` will call `doot.error(msg)` and then `sys.exit(1)` (you can
specify the exit code by passing `status`, the default is `1`).

```python
@doot.command(@doot.option("--name"))
def hello(args):
    if args.name.lower() in ("tyler", "steve", "james"):
        doot.fatal(f"Sorry, your name cannot be {args.name}. Get a new one.")
    print(f"Hello, {args.name}!")
```
