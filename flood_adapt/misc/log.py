import logging
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional


class FloodAdaptLogging:
    _DEFAULT_FORMATTER = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S %p",
    )
    _root_logger = logging.getLogger("FloodAdapt")

    def __init__(
        self,
        file_path: Optional[Path] = None,
        loglevel_console: int = logging.WARNING,
        loglevel_root: int = logging.INFO,
        loglevel_files: int = logging.DEBUG,
        formatter: logging.Formatter = _DEFAULT_FORMATTER,
        ignore_warnings: Optional[list[type[Warning]]] = None,
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

        if ignore_warnings:
            for warn_type in ignore_warnings:
                self.configure_warnings("ignore", category=warn_type)

    @classmethod
    def add_file_handler(
        cls,
        file_path: Path,
        loglevel: int = logging.DEBUG,
        formatter: Optional[logging.Formatter] = None,
    ) -> None:
        """Add a file handler to the logger that directs outputs to a the file."""
        if not file_path:
            raise ValueError("file_path must be provided.")
        file_path = Path(file_path)

        # check if the path is a only a filename
        if not file_path.parents:
            file_path = Path.cwd() / file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(filename=file_path, mode="a")
        file_handler.setLevel(loglevel)

        formatter = formatter or cls._DEFAULT_FORMATTER
        file_handler.setFormatter(formatter)

        cls.getLogger().addHandler(file_handler)

    @classmethod
    def remove_file_handler(cls, file_path: Path) -> None:
        """Remove a file handler from the logger, which stops sending logs to that file and closes it."""
        for handler in cls.getLogger().handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(
                file_path.resolve()
            ):
                handler.close()
                cls.getLogger().removeHandler(handler)

    @classmethod
    def getLogger(
        cls, name: Optional[str] = None, level: int = logging.INFO
    ) -> logging.Logger:
        """Get a logger with the specified name. If no name is provided, return the root logger.

        If the logger does not exist, it is created with the specified level.

        Parameters
        ----------
        name : str, optional
            The name of the logger. If not provided, the root logger is returned.
        level : int,
            The level of the logger. The default is logging.INFO.

        Returns
        -------
        logging.Logger
            The logger with the specified name.
        """
        if name is None:
            logger = cls._root_logger
        else:
            logger = logging.getLogger(f"FloodAdapt.{name}")
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
        file_path: Path,
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

    @classmethod
    def _close_file_handlers(cls, logger: logging.Logger, exclude: List[Path]) -> None:
        """Close and remove file handlers from a logger."""
        for handler in logger.handlers[:]:
            if (
                isinstance(handler, logging.FileHandler)
                and Path(handler.baseFilename) not in exclude
            ):
                handler.close()
                logger.removeHandler(handler)

    @classmethod
    def close_files(cls, exclude: List[Path] = []) -> None:
        """Close all file handlers except those in the exclude list."""
        cls._close_file_handlers(cls.getLogger(), exclude)
        cls._close_file_handlers(cls.getLogger("hydromt"), exclude)

    @classmethod
    def deprecation_warning(cls, version: str, reason: str):
        """Log a deprecation warning with reason and the version that will remove it."""
        warnings.warn(
            f"DeprecationWarning: {reason}. This will be removed in version {version}.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def configure_warnings(
        cls, action: str = "default", category: Optional[type[Warning]] = None
    ):
        """
        Configure the behavior of Python warnings.

        Parameters
        ----------
        action : str, optional
            The action to take on warnings. Common actions include 'ignore', 'default', 'error', 'always', etc.
            The default is 'default', which shows warnings once per triggering location.
        category : type[Warning], optional
            The category of warnings to configure. If not provided, all warnings are configured.
            categories include DeprecationWarning, UserWarning, RuntimeWarning, etc.

        """
        warnings.simplefilter(action=action, category=category)
