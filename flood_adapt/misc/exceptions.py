class FloodAdaptError(Exception):
    """Base class for all exceptions in the FloodAdapt module."""

    pass


class DatabaseError(FloodAdaptError):
    """Base class for exceptions raised in any database related files."""

    pass


class IsStandardObjectError(DatabaseError):
    """Raised when an operation is attempted on a standard object."""

    def __init__(
        self,
        name: str,
        object_type: str,
    ):
        msg = f"The {object_type} '{name}' is a standard object and cannot be modified or deleted."
        super().__init__(msg)


class AlreadyExistsError(DatabaseError):
    """Raised when an attempt is made to create an object that already exists."""

    def __init__(
        self,
        name: str,
        object_type: str,
    ):
        msg = f"The {object_type} '{name}' already exists."
        super().__init__(msg)


class DoesNotExistError(DatabaseError):
    """Raised when an attempt is made to access an object that does not exist."""

    def __init__(self, name: str, object_type: str):
        msg = f"The {object_type} '{name}' does not exist."
        super().__init__(msg)


class IsUsedInError(DatabaseError):
    """Raised when an attempt is made to delete or modify an object that is in use / referenced by another object."""

    def __init__(
        self, name: str, object_type: str, used_in_type: str, used_in: list[str]
    ):
        msg = f"The {object_type} '{name}' cannot be deleted/modified since it is already used in the {used_in_type}(s): {', '.join(used_in)}"
        super().__init__(msg)


class ConfigError(DatabaseError):
    """Raised when optional configuration, usually in the site, is missing or invalid."""

    def __init__(self, message: str):
        super().__init__(message)
