from typing import List, Optional, Type, TypeVar

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declared_attr

from core import APIException, db
from core.mixins.serializer import Attribute, Serializer
from core.mixins.single_pk import SinglePKMixin

UC = TypeVar('UC', bound='ClassMixin')


class ClassSerializer(Serializer):
    """
    The serializer object for a ``ClassMixin``. This can be ignored unless you
    add an attribute to the userclass not present in the ``ClassMixin``, in which
    case a new serializer should be assigned to the userclass model.
    """
    id = Attribute()
    name = Attribute()
    permissions = Attribute(permission='userclasses_modify')


class ClassMixin(SinglePKMixin):
    __serializer__ = ClassSerializer

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(24), nullable=False)
    permissions: List[str] = db.Column(ARRAY(db.String(36)), nullable=False, server_default='{}')

    @declared_attr
    def __table_args__(cls):
        return db.Index(f'ix_{cls.__tablename__}_name', func.lower(cls.name), unique=True),

    @classmethod
    def from_name(cls: Type[UC],
                  name: str) -> Optional[UC]:
        """
        Get a userclass object from its name.

        :param name: The name of the userclass
        :return:     The userclass
        """
        name = name.lower()
        return cls.query.filter(func.lower(cls.name) == name).scalar()

    @classmethod
    def new(cls: Type[UC],
            name: str,
            permissions: List[str] = None) -> UC:
        """
        Create a new userclass.

        :param name:        The name of the userclass
        :param permissions: The permissions to be attributed to the userclass
        :return:            The newly created userclass
        """
        if cls.from_name(name):
            raise APIException(f'Another {cls.__name__} already has the name {name}.')
        return super()._new(
            name=name,
            permissions=permissions or [])

    @classmethod
    def get_all(cls: Type[UC]) -> List[UC]:
        """
        Get all userclass objects.

        :return: A list of all userclasses of this class type
        """
        return cls.get_many(key=cls.__cache_key_all__)
