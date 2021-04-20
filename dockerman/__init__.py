__all__ = ['command', 'crun', 'main', 'option', 'run']

from . import dockerman
from .dockerman import (  # noqa
    command,
    crun,
    main,
    option,
    run,
)


def set_default_container(name):
    dockerman.default_container = name
