__all__ = [
    'command',
    'crun',
    'file',
    'log',
    'logcmd'
    'help',
    'info',
    'warning',
    'error',
    'main',
    'option',
    'run',
    'set_default_container',
]

from . import dockerman
from .dockerman import (  # noqa
    command,
    crun,
    file,
    log,
    logcmd,
    help,
    info,
    warning,
    error,
    main,
    option,
    run,
)


def set_default_container(name):
    dockerman.default_container = name
