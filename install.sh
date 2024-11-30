#!/usr/bin/env bash

project_name="Awesome Project"
dofile="./do"
shebang="#!/usr/bin/env python3"
install_location=".doot"

{ # this block ensures the entire file is downloaded before running
  write_dofile() {
    cat > "$dofile" << EOF
${shebang}

"""${project_name}.

Run \`${dofile} -h\` for a list of available tasks.
"""

import sys

sys.path.append("${install_location}")

import doot as do  # noqa: E402


@do.task(do.arg("-n", "--name", default="World"))
def hello(opt):
    print(f"Hello, {opt.name}!")


if __name__ == "__main__":
  do.exec(name="${dofile}", splash=sys.modules[__name__].__doc__.split("\n")[0])

EOF
    chmod +x "${dofile}"
  }

  install() {
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

    echo -n "Shebang [${shebang}]: "
    read temp_shebang

    if [ ! -z "${temp_shebang}" ]; then
      shebang=$temp_shebang;
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
