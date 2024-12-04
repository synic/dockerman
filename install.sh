#!/bin/sh

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

from doot import do  # pyright: ignore


@do.task(do.arg("-n", "--name", default="World"))
def hello(opt):
    """Say hi!"""
    do.info(f"Hello, {opt.name}!\n")


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

    do.success("Update complete!")
    do.log(" -> backup created at \`${install_location}/doot.py.bak\`")
    do.log(f" -> \`${install_location}/doot.py\` updated to \`{opt.ref}\` version")
    do.log("")


if __name__ == "__main__":
    do.exec()

EOF
    chmod +x "${dofile}"
  }

  validate_python_version() {
    # Find Python executable
    if command -v python3 >/dev/null 2>&1; then
      path_to_python="python3"
    elif command -v python >/dev/null 2>&1; then
      path_to_python="python"
    else
      printf "Unable to locate python executable. Is it in your \$PATH?\n"
      exit 1
    fi

    # Get version number
    version=$($path_to_python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")

    # Compare versions using sort -V
    if printf "%s\n%s\n" "$required_python_version" "$version" | sort -V -C; then
      # required_python_version <= version, which is what we want
      return 0
    else
      printf "Your python version %s is too old.\n" "$version"
      printf "%s or greater is required.\n" "$required_python_version"
      exit 1
    fi
  }

  install() {
    validate_python_version

    printf "Project name [%s]: " "${project_name}"
    read -r temp_project_name

    if [ -n "${temp_project_name}" ]; then
      project_name=$temp_project_name
    fi

    printf "Install location [%s]: " "${install_location}"
    read -r temp_install_location

    if [ -n "${temp_install_location}" ]; then
      install_location=$temp_install_location
    fi

    printf "Entrypoint: [%s]: " "${dofile}"
    read -r temp_dofile

    if [ -n "${temp_dofile}" ]; then
      dofile=$temp_dofile
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
