import logging
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Optional, TypeVar

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement
from flood_adapt.misc.exceptions import (
    AlreadyExistsError,
    DatabaseError,
    DoesNotExistError,
    IsStandardObjectError,
    IsUsedInError,
)
from flood_adapt.objects.object_model import Object

T_OBJECTMODEL = TypeVar("T_OBJECTMODEL", bound=Object)
logger = logging.getLogger(__name__)


class DbsTemplate(AbstractDatabaseElement[T_OBJECTMODEL]):
    display_name: str
    dir_name: str
    _object_class: type[T_OBJECTMODEL]
    _higher_lvl_object: str

    def __init__(
        self, database: IDatabase, standard_objects: Optional[list[str]] = None
    ):
        """Initialize any necessary attributes."""
        self._objects: dict[str, T_OBJECTMODEL] = {}
        self._mutated: set[str] = set()
        self._deleted: set[str] = set()
        self._last_modified: dict[str, datetime] = {}

        self._database = database
        self.input_path = database.input_path / self.dir_name
        self.output_path = database.output_path / self.dir_name
        self.standard_objects = standard_objects

    ## Public
    ## IO
    def load(self, names: list[str] | None = None):
        """Read all objects from self.input_path and add them to the in-memory database."""
        self.clear()

        if not self.input_path.exists():
            return

        for obj_dir in self.input_path.iterdir():
            path = obj_dir / f"{obj_dir.name}.toml"

            if names is not None and path.stem not in names:
                continue

            try:
                obj = self._read_object(path)
            except Exception as e:
                logger.warning(f"Failed to load {path} due to {e}, skipping...")
                continue

            self._last_modified[path.stem] = datetime.fromtimestamp(
                path.stat().st_mtime
            )
            self.add(obj)

        # Loading should not mark mutations
        self._mutated.clear()
        self._deleted.clear()

    def flush(self):
        """Write all staged changes to disk."""
        self.input_path.mkdir(parents=True, exist_ok=True)

        for name in self._mutated:
            obj = self._objects[name]
            path = self.input_path / name / f"{name}.toml"

            # To avoid issues with editing objects, we first write the new version to a temporary dir,
            # then delete the old dir, and finally move the new dir to the correct location.
            # This way, the old version is not deleted until the new version is successfully written,
            # and additional files can be copied from the old version to the new version,
            # before the old version is deleted.
            tmp_path = (
                Path(gettempdir())
                / f"{name}_{datetime.now().timestamp()}"
                / f"{name}.toml"
            )
            self._write_object(obj, tmp_path)

            try:
                if path.parent.exists():
                    shutil.rmtree(path.parent)
            except OSError as e:
                raise DatabaseError(
                    f"Failed to delete input for `{name}` due to: {e}"
                ) from e

            try:
                if (self.output_path / name).exists():
                    shutil.rmtree(self.output_path / name)
            except OSError as e:
                raise DatabaseError(
                    f"Failed to delete output for `{name}` due to: {e}"
                ) from e

            try:
                shutil.move(tmp_path.parent, path.parent)
            except OSError as e:
                raise DatabaseError(
                    f"Failed to move temporary file for `{name}` due to: {e}"
                ) from e

            self._last_modified[name] = datetime.now()

        for name in self._deleted:
            try:
                if (self.input_path / name).exists():
                    shutil.rmtree(self.input_path / name)
            except OSError as e:
                raise DatabaseError(
                    f"Failed to delete input for `{name}` due to: {e}"
                ) from e

            try:
                if (self.output_path / name).exists():
                    shutil.rmtree(self.output_path / name)
            except OSError as e:
                raise DatabaseError(
                    f"Failed to delete output for `{name}` due to: {e}"
                ) from e

            self._last_modified.pop(name, None)

        self._mutated.clear()
        self._deleted.clear()

    def used_by_higher_level(self, name: str) -> list[str]:
        """Check if an object is used in a higher level object.

        Parameters
        ----------
        name : str
            name of the object to be checked

        Returns
        -------
        list[str]
            list of higher level objects that use the object
        """
        # If this function is not implemented for the object type, it cannot be used in a higher
        # level object. By default, return an empty list
        return []

    def list_all(self) -> list[T_OBJECTMODEL]:
        """Return a list of all objects that currently exist in the database."""
        return list(self._objects.values())

    ## In memory mutation
    def add(self, obj: T_OBJECTMODEL, overwrite: bool = False):
        """Add an object to the in-memory database, and mark it for addition during the next flush.

        Parameters
        ----------
        obj : Object
            object to be added to the database
        overwrite : bool, optional
            whether to overwrite an existing object with the same name, by default False

        Raises
        ------
        AlreadyExistsError
            Raise error if name is already in use and overwrite is False.
        IsStandardObjectError
            Raise error if object to be added is a standard object and overwrite is True.
        IsUsedInError
            Raise error if object to be added is already in use and overwrite is True.
        """
        self._assert_can_be_added(obj, overwrite=overwrite)
        self._objects[obj.name] = obj
        self._mutated.add(obj.name)

    def copy(self, old_name: str, new_name: str, new_description: str):
        """Copy (duplicate) an existing object, and give it a new name.

        Parameters
        ----------
        old_name : str
            name of the existing measure
        new_name : str
            name of the new measure
        new_description : str
            description of the new measure

        Raises
        ------
        AlreadyExistsError
            Raise error if an object with the new name already exists.
        IsStandardObjectError
            Raise error if an object with the new name is a standard object.
        DatabaseError
            Raise error if the saving of the object fails.
        """
        source = self.get(old_name).model_copy(deep=True)
        source.name = new_name
        source.description = new_description
        source.model_validate(source)

        self.add(source)

    def delete(self, name: str):
        """Delete an already existing object from the in-memory database and mark it for deletion during the next flush.

        Parameters
        ----------
        name : str
            name of the object to be deleted

        Raises
        ------
        IsStandardObjectError
            Raise error if object to be deleted is a standard object.
        IsUsedInError
            Raise error if object to be deleted is already in use.
        DoesNotExistError
            Raise error if object to be deleted does not exist.
        DatabaseError
            Raise error if the deletion of the object fails.
        """
        self._assert_can_be_deleted(name)

        # Once all checks are passed, delete the object
        del self._objects[name]
        self._deleted.add(name)
        self._mutated.discard(name)

    def get(self, name: str) -> T_OBJECTMODEL:
        """Return an object of the type of the database with the given name.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        Object
            object of the type of the specified object model

        Raises
        ------
        DoesNotExistError
            Raise error if the object does not exist.
        """
        self._assert_has_object(name)
        return self._objects[name].model_copy(deep=True)

    def clear(self):
        """Clear the in-memory database, without deleting any files on disk. This will unstage any staged changes."""
        self._objects.clear()
        self._mutated.clear()
        self._deleted.clear()
        self._last_modified.clear()

    ## Query / Info methods
    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the objects that currently exist in the database.

        Returns
        -------
        dict[str, list[Any]]
            A dictionary that contains the keys: `name`, `description`, `path`  and `last_modification_date`.
            Each key has a list of the corresponding values, where the index of the values corresponds to the same object.
        """
        names = list(self._objects)
        paths = [self.input_path / name / f"{name}.toml" for name in names]
        descriptions = [obj.description for obj in self._objects.values()]
        last_modification_date = [self._last_modified.get(name) for name in names]
        objects = {
            "name": names,
            "description": descriptions,
            "path": paths,
            "last_modification_date": last_modification_date,
        }
        return objects

    ## Private methods
    def _read_object(self, path: Path) -> T_OBJECTMODEL:
        """Read object from disk, overwritable function that is called in `flush`."""
        return self._object_class.load_file(path)

    def _write_object(self, obj: T_OBJECTMODEL, path: Path) -> None:
        """Write object to disk, overwritable function that is called in `flush`."""
        path.parent.mkdir(parents=True, exist_ok=True)
        obj.save(path)

    # Helpers
    def _is_standard_object(self, name: str) -> bool:
        """Check if an object is a standard object.

        Parameters
        ----------
        name : str
            name of the object to be checked

        Returns
        -------
        bool
            True if the object is a standard object, False otherwise
        """
        if self.standard_objects:
            return name in self.standard_objects
        return False

    def _has_object(self, name: str) -> bool:
        """Check if an object with the given name exists in the database."""
        return name in self._objects

    # Validation
    def _assert_can_be_added(
        self, object_model: T_OBJECTMODEL, overwrite: bool
    ) -> None:
        """Validate if the object can be added to the database and raise appropriate errors if not."""
        if self._has_object(object_model.name):
            if overwrite:
                self._assert_can_be_deleted(object_model.name)
            else:
                raise AlreadyExistsError(object_model.name, self.display_name)

    def _assert_can_be_deleted(self, name: str) -> None:
        """Validate if the object can be deleted from the database and raise appropriate errors if not."""
        if self._is_standard_object(name):
            raise IsStandardObjectError(name, self.display_name)

        if used_in := self.used_by_higher_level(name):
            raise IsUsedInError(
                name, self.display_name, self._higher_lvl_object, used_in
            )

        if name not in self._objects:
            raise DoesNotExistError(name, self.display_name)

    def _assert_has_object(self, name: str) -> None:
        """Validate if the object exists in the database and raise an error if not."""
        if not self._has_object(name):
            raise DoesNotExistError(name, self.display_name)

    def __del__(self):
        if self._mutated or self._deleted:
            logger.warning("Database object destroyed with unflushed changes.")
