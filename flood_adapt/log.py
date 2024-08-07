import logging
import os
from contextlib import contextmanager


class FloodAdaptLogging:
    _DEFAULT_FORMATTER = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S %p",
    )
    _root_logger = logging.getLogger("FloodAdapt")

    def __init__(
        self,
        file_path: str = None,
        loglevel_console: int = logging.WARNING,
        loglevel_root: int = logging.INFO,
        loglevel_files: int = logging.DEBUG,
        formatter: logging.Formatter = _DEFAULT_FORMATTER,
    ) -> None:
        """Initialize the logging system for the FloodAdapt."""
        self._formatter = formatter

        self._root_logger.setLevel(loglevel_root)
        if self._root_logger.hasHandlers():
            self._root_logger.handlers.clear()

        # Add file handler if provided
        if file_path is not None:
            self.add_file_handler(file_path, loglevel_files, formatter)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(loglevel_console)
        console_handler.setFormatter(formatter)
        self._root_logger.addHandler(console_handler)

    @classmethod
    def add_file_handler(
        cls,
        file_path: str,
        loglevel: int = logging.DEBUG,
        formatter: logging.Formatter = None,
    ) -> None:
        """Add a file handler to the logger that directs outputs to a the file."""
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        file_handler = logging.FileHandler(filename=file_path, mode="a")
        file_handler.setLevel(loglevel)

        formatter = formatter or cls._DEFAULT_FORMATTER
        file_handler.setFormatter(formatter)

        cls.getLogger().addHandler(file_handler)

    @classmethod
    def remove_file_handler(cls, file_path: str) -> None:
        """Remove a file handler from the logger, which stops sending logs to that file and closes it."""
        for handler in cls.getLogger().handlers:
            if isinstance(
                handler, logging.FileHandler
            ) and handler.baseFilename == os.path.abspath(file_path):
                handler.close()
                cls.getLogger().removeHandler(handler)

    @classmethod
    def getLogger(cls, name: str = None, level: int = None) -> logging.Logger:
        """Get a logger with the specified name. If no name is provided, return the root logger.

        If the logger does not exist, it is created with the specified level. If no level is provided, the logger inherits the level of the root logger.

        Parameters
        ----------
        name : str, optional
            The name of the logger. If not provided, the root logger is returned.
        level : int, optional
            The level of the logger. If not provided, the logger inherits the level of the root logger.

        Returns
        -------
        logging.Logger
            The logger with the specified name.
        """
        if name is None:
            logger = cls._root_logger
        else:
            logger = logging.getLogger(f"FloodAdapt.{name}")

        if level is not None:
            logger.setLevel(level)

        return logger

    @classmethod
    def shutdown(cls):
        root_logger = cls.getLogger()
        handlers = root_logger.handlers[:]
        for handler in handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)
        logging.shutdown()

    @classmethod
    @contextmanager
    def to_file(
        cls,
        *,
        file_path: str = None,
        loglevel: int = logging.DEBUG,
        formatter: logging.Formatter = _DEFAULT_FORMATTER,
    ):
        """Open a file at filepath to write logs to. Does not affect other loggers.

        When the context manager exits (via regular execution or an exception), the file is closed and the handler is removed.
        """
        if file_path is None:
            raise ValueError(
                "file_path must be provided as a key value pair: 'file_path=<file_path>'."
            )
        cls.add_file_handler(file_path, loglevel, formatter)
        try:
            yield
        finally:
            cls.remove_file_handler(file_path)
