from abc import abstractmethod
from pathlib import Path

from flood_adapt.misc.database_user import DatabaseUser
from flood_adapt.objects.scenarios.scenarios import Scenario


class IAdapter(DatabaseUser):
    """Adapter interface for all models run in FloodAdapt."""

    @abstractmethod
    def has_run(self, scenario: Scenario) -> bool:
        """Return True if the model has been run."""
        pass

    @abstractmethod
    def __enter__(self) -> "IAdapter":
        """Use the adapter as a context manager to handle opening and closing of the model and attached resources like logfiles.

        Returns
        -------
            self: the adapter object

        Usage
        -----
        >>> with Adapter(...) as model:
        >>>     ...
        >>>     model.get_result(...)
        >>>     model.run(...)

        Entering the with block will call adapter.__enter__() and
        Exiting the with block (via regular execution or an error) will call adapter.__exit__()
        """
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """Close the model and release any resources.

        Usage
        -----
        >>> with Adapter as model:
        >>>     ...
        >>>     model.run()

        Entering the `with` block will call adapter.__enter__()
        Exiting the `with` block (via regular execution or an error) will call adapter.__exit__()

        Returns
        -------
            False to propagate/reraise any exceptions that occurred in the with block
            True to suppress any exceptions that occurred in the with block
        """
        pass

    @abstractmethod
    def read(self, path: Path):
        """Read the model configuration from a path or other source."""
        pass

    @abstractmethod
    def write(self, path_out: Path, overwrite: bool = True):
        """Write the current model configuration to a path or other destination."""
        pass

    @abstractmethod
    def run(self, scenario: Scenario):
        """Perform the whole workflow (preprocess, execute and postprocess) of running the model."""
        pass

    @abstractmethod
    def preprocess(self, scenario: Scenario):
        """Prepare the model for execution."""
        pass

    @abstractmethod
    def execute(self, path: Path, strict: bool = True) -> bool:
        """Run the model kernel at the specified path.

        Returns True if the model ran successfully, False otherwise.

        If strict is True, raise an exception if the model fails to run.
        """
        pass

    @abstractmethod
    def postprocess(self, scenario: Scenario):
        """Process the model output."""
        pass
