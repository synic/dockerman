# Complex Doot Script Example

Here's a more complex setup for a node app running in docker:

```python
#!/usr/bin/env python3

"""Awesome project example.
                     _
__      _____   ___ | |_
\ \ /\ / / _ \ / _ \| __|
 \ V  V / (_) | (_) | |_
  \_/\_/ \___/ \___/ \__|
"""  # noqa

import json
import pathlib
import os
import subprocess
import sys

if not os.path.isfile("./lib/doot/doot/__init__.py"):
    print("`doot` not found; run `git submodule update --init`")
    sys.exit(1)

sys.path.append("./lib/doot")

import doot as do  # noqa: E402

# enable buildkit
os.environ["DOCKER_BUILDKIT"] = "1"
os.environ["COMPOSE_DOCKER_CLI_BUILD"] = "1"


@do.task(passthrough=True)
def bash(opts):
    """Bash shell on the api container."""
    do.run("docker exec -it api bash", opts.args)


@do.task()
def start():
    """Start all services."""
    data = subprocess.check_output(["docker", "network", "list", "-f", "name=awesome"])
    if "awesome" not in data.decode():
        do.run("docker network create awesome")
    do.run("docker-compose up -d")


@do.task(passthrough=True)
def logs(opts):
    """Show logs for main api container."""
    do.run(f"docker logs -f -n 1000 {cont.api}", opts.args)


@do.task()
def stop():
    """Stop all services."""
    do.run("docker-compose stop")


@do.task()
def db():
    """Execute a database shell."""
    do.run("docker exec -it database psql -U postgres postgres")


@do.task()
def debug():
    """Attach to api container for debugging."""
    do.warning(f"Attaching to `{cont.api}`. Type CTRL-p CTRL-q to exit.")
    do.warning("CTRL-c will restart the container.")
    do.run(f"docker attach {cont.api}")


@do.task(passthrough=True)
def lint(opts):
    """Lint the code."""
    do.run("docker exec -it api yarn lint", opts.args)


@do.task(passthrough=True)
def typeorm(opts):
    """Run migration commands."""
    do.run("docker exec -it api yarn typeorm:cli", opts.args)


@do.task()
def migrate(opts):
    """Run all migrations."""
    do.run("docker exec -it yarn typeorm:cli migration:run", opts.args)


@do.task(passthrough=True)
def yarn(opts):
    """Run yarn commands."""
    do.run("docker exec -it yarn", opts.args)


@do.task(passthrough=True)
def manage(opts):
    """Run management commands."""
    do.run("docker exec -it yarn manage", opts.args)


@do.task(do.arg("-n", "--name", help="migration file base name"))
def createmigration(opts):
    """Create a migration with a name."""
    do.run(
        "docker exec -it api"
        f"yarn typeorm:plaincli migration:create "
        f"./src/databases/migrations/default/{opts.name}",
        opts.args,
    )


@do.task(do.arg("-n", "--name", help="migration file base name"))
def generatemigration(opts):
    """Generate a migration with a name."""
    do.run(
        "docker exec -it api"
        f"yarn typeorm:cli migration:generate "
        f"./src/databases/migrations/default/{opts.name}",
        opts.args,
    )


def get_latest_image_data(environment="staging"):
    region = "us-west-2" if environment == "staging" else "us-east-2"
    repo = f"{environment}-prices"

    data = subprocess.check_output(
        ["aws", "ecr", "list-images", "--repository-name", repo, "--region", region]
    )

    items = json.loads(data)["imageIds"]
    latest_tag = None
    latest_tag_time = 0

    for item in items:
        try:
            tag = item["imageTag"]
            (branch, ref, ts) = tag.split("-")
        except (KeyError, ValueError):
            continue

        if int(ts) > latest_tag_time:
            latest_tag = (tag, branch, ref, int(ts))
            latest_tag_time = int(ts)

    return latest_tag


@do.task(
    do.arg("-t", "--tag", default=None, help="Optional staging tag"),
    do.arg("-d", "--diff", action="store_true", help="Show diff"),
)
def release(opts):
    """Release the staging image to production."""

    prod_info = get_latest_image_data("production")
    tag = opts.tag

    if tag:
        stage_info = (tag,) + tuple(tag.split("-"))
    else:
        stage_info = get_latest_image_data("staging")

    if not prod_info:
        do.error("Could not find production image tag")
        sys.exit(1)

    if not stage_info:
        do.error("Could not find staging image tag")
        sys.exit(1)

    do.info(f"\nProduction tag: {prod_info[0]}")
    do.info(f"Staging tag: {stage_info[0]}\n")

    if stage_info[0] == prod_info[0]:
        do.error("\nImages are the same, nothing to release.")
        sys.exit(1)

    do.run("git fetch")
    do.log("\n")
    do.run(f"git log --oneline {prod_info[2]}..{stage_info[2]}")

    if opts.diff:
        do.run(f"git diff -u {prod_info[2]}..{stage_info[2]}")

    res = input("\nIf you're sure you want to release, type YES\nAnswer: ")

    do.log("\n\n")
    if res.strip().lower() == "yes":
        do.run(f"./scripts/release-production.sh {stage_info[0]}")
    else:
        do.error("ok bye")


def get_active_branch_name():
    head_dir = pathlib.Path(".") / ".git" / "HEAD"
    with head_dir.open("r") as f:
        content = f.read().splitlines()

    for line in content:
        if line[0:4] == "ref:":
            return line.partition("refs/heads/")[2]


@do.task(do.arg("-p", "--push", action="store_true", help="Execute a git push first"))
def pr(opts):
    """Opens a PR with the current branch.

    Only works on Mac/Linux for the time being.
    """
    branch = get_active_branch_name()
    cmd = "open" if sys.platform.lower() == "darwin" else "xdg-open"

    if sys.platform.lower() not in ("darwin", "linux"):
        do.error(f"This command is not currently supported on {sys.platform}.")
        sys.exit(1)

    if branch in (None, "", "main"):
        do.error(f"Cannot create a PR for the branch {branch}.")
        sys.exit(1)

    if opts.push:
        os.system("git push")

    url = f"https://github.com/awesome/awesome/compare/{branch}?expand=1"
    do.info(f"Opening {url} ... \n")
    os.system(f"{cmd} {url}")


@do.task()
def pod():
    """Shell into a kubernetes pod."""
    pod = subprocess.check_output(
        [
            "kubectl",
            "get",
            "pods",
            "-l",
            "app=awesome",
            "-A",
            "-o",
            'jsonpath="{.items[0].metadata.name}"',
        ],
        text=True,
    )
    if not pod:
        do.fatal("Could not find `awesome` pod.")

    do.run(f"kubectl exec -n awesome -ti {str(pod)} -- /bin/bash")


@do.task()
def build_essential(opts):
    """Install build deps for native node packages."""
    do.run("docker exec -it api apt update", opts.args)
    do.run("docker exec -it apt install build-essential", opts.args)


if __name__ == "__main__":
    module = sys.modules[__name__]
    splash = "\n".join(module.__doc__.split("\n")[1:-1])
    do.exec(splash=splash)
```
