# Docker Management For Python Applications

This library is intended to make it easier to develop web applications when
using docker. It allows you to set up initial docker configuration, and to
execute commands inside the main docker container. It aims to be similar to
[Fabric](https://fabfile.org), but for local development with docker
applications.

## Getting Started

A typical setup looks something like this:

1. A `docker-compose.yml` (or a docker setup that has been created manually)
   with at least one "main" python container. For instance, if you are
   developing a web application, you might have a `redis` container, a
   `database` container, and a `web` container, and the `web` container is the
   one that contains your python code. You can also use custom `@dm.command`
   functions to set up your docker cluster without docker-compose, if you want.
2. A script that is the entrypoint for your management command. I typically use
   `./do` in the project's root directory. It looks something like this:

   ```python

    #!/usr/bin/env python

    import os

    import dockerman as dm

    # enable buildkit
    os.environ["DOCKER_BUILDKIT"] = "1"
    os.environ["COMPOSE_DOCKER_CLI_BUILD"] = "1"


    @dm.command(passthrough=True)
    def bash(args):
        """Bash shell on the web container."""
        dm.crun("bash", args)


    @dm.command()
    def start(args):
        """Start all services."""
        dm.run("docker-compose up -d")


    @dm.command()
    def stop(args):
        """Stop all services."""
        dm.run("docker-compose stop")


    @dm.command()
    def dbshell(args):
        """Execute a database shell."""
        dm.crun("psql -U myuser mydatabase", container="database")


    @dm.command()
    def shell(args):
        """Open a django shell on the web container."""
        dm.crun("django-admin shell", args)


    @dm.command(passthrough=True)
    def manage(args):
        """Run a django management command."""
        dm.crun("django-admin", args)


    @dm.command(
        dm.option('--name', help='Container name'),
    )
    def reset_container(args):
        """Reset a container."""
        dm.run(f"docker-compose stop {args.name}")
        dm.run(f"docker-compose rm {args.name}")
        dm.run("docker-compose up -d")


    if __name__ == "__main__":
        dm.set_default_container("web")
        dm.main()
     ```

With this setup, you can run commands like `./do help`, `./do shell`, etc.

## Concepts

### `dm.command`

This is a decorator that turns a function into a command. The command will have
the same name as the function it decorates, and the docstring will be the
documentation that appears when you type `./do help` or `./do help [command]`.
All underscores will be converted to hyphens in the resulting command name.

If you specify `passthrough=True`, all extra command line arguments will be
passed to any `dm.crun` or `dm.run` statements executed within the function
(this is the purpose of the command function receiving the `args` parameter,
and passing that same `args` parameter to `dm.crun` and `dm.run`).

For example, if you'd like to run Django management commands in the web
container:

```python
@dm.command(passthrough=True)
def manage(args):
    """Run Django management commands."""
    dm.crun("django-admin", args)
```

Then when you run something like:

```bash
$ ./do manage makemigrations --name add_user_is_active_field accounts
```

The `makemigrations --name add_user_is_active_field accounts` will be passed
through to `django-admin` on the container.

#### Default Commands

Another possible argument to `@dm.command` is `default=True`. This will cause
the system to use this command for everything that doesn't match any other
command. For instance, instead of defining a `shell` command for django-admin,
you could do the following:

```python
@dm.command(passthrough=True, default=True)
def manage(args):
    """Run Django management commands."""
    dm.crun("django-admin", args)
```

Then, if you type `./do shell` and there is no matching `shell` command
defined, it will act as though you typed `./do manage shell`.

### `dm.run`

This runs a command on the host. Things like
`dm.run('docker network add test')` are typical.

### `dm.crun`

This runs a command in a docker container. Passing `container="web"` will tell
it to run on the "web" container. If you do not pass `container`, it will use
the default container specified in `dm.set_default_container`.

### `dm.option`

You can pass one or more `dm.option` arguments to the `dm.command` decorator.
These will set up argument options for your command, using the `argparse`
module. They are passed directly to `parser.add_argument`, so they have the
same parameters.

An example:

```python

@dm.command(@dm.option("--name", dest="name", help="Your name"))
def hello(args):
    print(f"Hello, {args.name}!")
```

### `dm.log`, `dm.info`, `dm.warning`, `dm.error`

These are logging statements. Each one has it's own color indicative of the
type of message you want to show. For example:


```python
@dm.command(@dm.option("--name"))
def hello(args):
    if args.name.lower() in ("tyler", "steve", "james"):
        dm.error(f"Sorry, your name cannot be {args.name}. Get a new one.")
        sys.exit(1)
    print(f"Hello, {args.name}!")
```
