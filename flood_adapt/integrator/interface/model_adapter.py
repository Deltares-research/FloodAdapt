import os
from abc import abstractmethod
from enum import Enum

from flood_adapt.object_model.interface.database_user import IDatabaseUser
from flood_adapt.object_model.interface.scenarios import IScenario


class ModelData(str, Enum):
    pass


class IAdapter(IDatabaseUser):
    """Adapter interface for all models run in FloodAdapt."""

    @property
    @abstractmethod
    def has_run(self) -> bool:
        """Return True if the model has been run."""
        pass

    @abstractmethod
    def __enter__(self) -> "IAdapter":
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
    def read(self, path: str | os.PathLike):
        """Read the model configuration from a path or other source."""
        pass

    @abstractmethod
    def write(self, path: str | os.PathLike):
        """Write the current model configuration to a path or other destination."""
        pass

    @abstractmethod
    def run(self, scenario: IScenario):
        """Perform the whole workflow (preprocess, execute and postprocess) of running the model."""
        pass

    @abstractmethod
    def preprocess(self):
        """Prepare the model for execution."""
        pass

    @abstractmethod
    def execute(self):
        """Execute a model run without any further processing."""
        pass

    @abstractmethod
    def postprocess(self):
        """Process the model output."""
        pass
