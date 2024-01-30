"""Common db utils."""

class UnexpectedCase(RuntimeError):
    def __init__(self, other):
        super().__init__("Unexpected case: %r" % other)
