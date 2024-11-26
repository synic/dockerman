class Option:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class File(object):
    def __init__(self, fn):
        if fn.lower().endswith(".sql"):
            self.fmt = "sql"
        elif fn.lower().endswith(".json"):
            self.fmt = "json"
        else:
            raise ValueError("Invalid file import extension")
        self.fn = fn

    def __str__(self):
        return self.fn


class Config:
    def __init__(self):
        self.default_command = None
        self.default_container = None
        self.prog_name = "./do"
        self.splash = ""
