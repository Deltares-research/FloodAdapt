import os
from abc import ABC, abstractmethod
from enum import Enum


class ModelData(str, Enum):
    pass


class IAdapter(ABC):
    @abstractmethod
    def __enter__(self):
        """Use the adapter as a context manager to handle opening/closing of the model and attached resources.

        This method should return the adapter object itself, so that it can be used in a with statement.

        Usage:

        with Adapter as model:
            ...
            model.run()

        Entering the with block will call adapter.__enter__() and
        Exiting the with block (via regular execution or an error) will call adapter.__exit__()
        """
        pass

    @abstractmethod
    def __exit__(self):
        """Use the adapter as a context manager to handle opening/closing of the model and attached resources.

        This method should return the adapter object itself, so that it can be used in a with statement.

        Usage:

        with Adapter as model:
            ...
            model.run()

        Entering the `with` block will call adapter.__enter__()
        Exiting the `with` block (via regular execution or an error) will call adapter.__exit__()
        """
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self, path: str | os.PathLike):
        pass

    @abstractmethod
    def run(self):
        pass
