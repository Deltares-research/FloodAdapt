class FloodAdaptError(Exception):
    """Base class for all exceptions in the FloodAdapt module."""

    pass


class DatabaseError(FloodAdaptError):
    """Base class for exceptions raised in any database related files."""

    pass


class ComponentError(FloodAdaptError):
    """Base class for exceptions raised in any component/object related files."""

    pass


class WorkflowError(FloodAdaptError):
    """Base class for exceptions raised in any workflow related files."""

    pass
