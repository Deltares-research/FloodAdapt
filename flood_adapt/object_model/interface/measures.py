from abc import ABC, abstractmethod
import typing
import os
import pydantic

class Elevation(pydantic.BaseModel): # TODO this should be imported from the general pydantic defenitions in the object model
    value: float
    units: str
    type: str

class IElevate(ABC):
    @property
    @abstractmethod
    def name(self):
        ...

    @name.setter
    @abstractmethod
    def name(self, value: str):
        ...  

    @property
    @abstractmethod
    def long_name(self):
        ...

    @long_name.setter
    @abstractmethod
    def long_name(self, value: str):
        ...  

    @property
    @abstractmethod
    def type(self):
        ...

    @type.setter
    @abstractmethod
    def type(self, value: str):
        ...  

    @property
    @abstractmethod
    def elevation(self):
        ...

    @elevation.setter
    @abstractmethod
    def elevation(self, value: Elevation):
        ... 

    @property
    @abstractmethod
    def selection_type(self):
        ...

    @selection_type.setter
    @abstractmethod
    def selection_type(self, value: str):
        ...

    @property
    @abstractmethod
    def aggregation_area(self):
        ...

    @aggregation_area.setter
    @abstractmethod
    def aggregation_area(self, value: str):
        ...  

    @property
    @abstractmethod
    def polygon_file(self):
        ...

    @polygon_file.setter
    @abstractmethod
    def polygon_file(self, value: str):
        ...  

    @property
    @abstractmethod
    def property_type(self):
        ...

    @property_type.setter
    @abstractmethod
    def property_type(self, value: str):
        ...  

    @abstractmethod
    def load(self, config_file: typing.Union[str, os.PathLike]):
        ...

    @abstractmethod
    def get_object_ids(self) -> list[any]:
        ...
