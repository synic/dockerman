#!/usr/bin/env bash

project_name="Awesome Project"
dofile="./do"
shebang="#!/usr/bin/env python3"
install_location=".doot"
required_python_version="3.8.0"

{ # this block ensures the entire file is downloaded before running
  write_dofile() {
    cat > "$dofile" << EOF
${shebang}

"""${project_name}.

Run \`${dofile} -h\` for a list of available tasks.
"""

import shutil
import sys
import urllib.request

sys.path.append("${install_location}")

import doot as do  # noqa: E402


@do.task(do.arg("-n", "--name", default="World"))
def hello(opt):
    """Say hi!"""
    print(f"Hello, {opt.name}!")


@do.task(do.arg("-r", "--ref", help="Git ref to install [main]", default="main"))
def doot__update(opt):
    """Update doot at \`${install_location}/doot.py\` to a different version."""
    res = input("\nIf you're sure you want to update, type YES\nAnswer: ")

    do.log("")

    if res.strip().lower() != "yes":
        do.log("Update cancelled. Bye!")
        sys.exit()

    url = f"https://raw.githubusercontent.com/synic/doot/{opt.ref}/doot.py"
    shutil.move("${install_location}/doot.py", "${install_location}/doot.py.bak")

    with urllib.request.urlopen(url) as res:
        with open("${install_location}/doot.py", "w") as h:
            h.write(res.read().decode('utf8'))

    do.info("Update complete!")


if __name__ == "__main__":
  do.exec(name="${dofile}", splash=sys.modules[__name__].__doc__.split("\n")[0])

EOF
    chmod +x "${dofile}"
  }

  verlte() {
    [ "$1" = "`echo -e "$1\n$2" | sort -V | head -n1`" ]
  }

  verlt() {
    [ "$1" = "$2" ] && return 1 || verlte $1 $2
  }

  validate_python_version() {
    path_to_python=$(which python3)

    if [ -z "${path_to_python}" ]; then
      path_to_python=$(which python)
    fi

    if [ -z "${path_to_python}" ]; then
      echo "Unable to locate python executable. Is it in your \$PATH?"
      exit 1
    fi

    output=$(bash -c "${path_to_python} --version")
    version="${output##* }"

    if verlt "${version}" "${required_python_version}"; then
      echo "Your python version \`${version}\` is too old."
      echo "\`${required_python_version}\` or greater is required."
      exit 1
    fi
  }

  install() {
    validate_python_version

    echo -n "Project name [${project_name}]: "
    read temp_project_name

    if [ ! -z "${temp_project_name}" ]; then
      project_name=$temp_project_name;
    fi

    echo -n "Install location [${install_location}]: "
    read temp_install_location

    if [ ! -z "${temp_install_location}" ]; then
      install_location=$temp_install_location;
    fi

    echo -n "Entrypoint: [${dofile}]: "
    read temp_dofile

    if [ ! -z "${temp_dofile}" ]; then
      dofile=$temp_dofile;
    fi

    curl --create-dirs -O --output-dir "${install_location}" \
      https://raw.githubusercontent.com/synic/doot/main/doot.py

    write_dofile
  }

  install
  echo
  echo "Installation complete!"
  echo
  echo "Run \`${dofile} -h\` to use your new task file!"
}
