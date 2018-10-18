from typing import Any, Optional, Type, TypeVar, TYPE_CHECKING
from enum import Enum

from flask_sqlalchemy import BaseQuery, Model
from sqlalchemy.orm.session import make_transient_to_detached
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy import func
from sqlalchemy.orm.attributes import InstrumentedAttribute

from core import cache, db

if TYPE_CHECKING:
    from core.mixins.serializer import Serializer  # noqa: F401

PKB = TypeVar('PKB', bound='PKBase')


class BaseFunctionalityMixin:

    @classmethod
    def assign_attrs(cls, **kwargs):
        for key, val in kwargs.items():
            setattr(cls, key, val)


class TestDataPopulator:

    @staticmethod
    def add_permissions(*permissions):
        permissions = [p if not isinstance(p, Enum) else p.value for p in permissions]
        db.engine.execute(
            f"""INSERT INTO users_permissions (user_id, permission) VALUES
            (1, '""" + "'), (1, '".join(permissions) + "')")


class PKBase(Model, BaseFunctionalityMixin):
    """
    A base class for the primary key mixin types. Contains their shared code and
    some attributes present in both.
    """

    __cache_key__: Optional[str] = None
    __deletion_attr__: Optional[str] = None
    __serializer__: Optional[Type['Serializer']] = None

    @classmethod
    def from_cache(cls,
                   key: str,
                   *,
                   query: BaseQuery = None) -> Optional[PKB]:
        data = cache.get(key)
        obj = cls._create_obj_from_cache(data)
        if obj:
            return obj
        else:
            cache.delete(key)
        if query:
            obj = query.scalar()
            cache.cache_model(obj)
        return obj

    @classmethod
    def _create_obj_from_cache(cls: Type[PKB],
                               data: Any) -> Optional[PKB]:
        if cls._valid_data(data):
            obj = cls(**data)
            make_transient_to_detached(obj)
            obj = db.session.merge(obj, load=False)
            return obj
        return None

    @classmethod
    def _valid_data(cls, data: dict) -> bool:
        """
        Validate the data returned from the cache by ensuring that it is a dictionary
        and that the returned values match the columns of the object.

        :param data: The stored object data from the cache to validate
        :return:     Whether or not the data is valid
        """
        return (bool(data)
                and isinstance(data, dict)
                and set(data.keys()) == set(cls.__table__.columns.keys()))

    @staticmethod
    def _construct_query(query: BaseQuery,
                         filter: BinaryExpression = None,
                         order: BinaryExpression = None) -> BaseQuery:
        """
        A convenience function to save code space for query generations. Takes filters
        and order_bys and applies them to the query, returning a query ready to be ran.

        :param query:  A query that can be built upon
        :param filter: A SQLAlchemy query filter expression
        :param order:  A SQLAlchemy query order_by expression

        :return:       A Flask-SQLAlchemy ``BaseQuery``
        """
        if filter is not None:
            query = query.filter(filter)
        if order is not None:
            query = query.order_by(order)
        return query

    @classmethod
    def _new(cls: Type[PKB], **kwargs: Any) -> PKB:
        """
        Create a new instance of the model, add it to the instance, and return it.

        :param kwargs: The new attributes of the model
        """
        model = cls(**kwargs)
        db.session.add(model)
        db.session.commit()
        if cls.__cache_key__:
            cache.cache_model(model)
        return model

    @classmethod
    def count(cls,
              *,
              key: str,
              attribute: InstrumentedAttribute,
              filter: BinaryExpression = None) -> int:
        """
        An abstracted function for counting a number of elements matching a query. If the
        passed cache key exists, its value will be returned; otherwise, the passed query
        will be ran and the resultant count cached and returned.

        :param key:       The cache key to check
        :param attribute: The attribute to count; a model's column
        :param filter:    The SQLAlchemy filter expression

        :return: The number of rows matching the query element
        """
        count = cache.get(key)
        if not isinstance(count, int):
            query = cls._construct_query(db.session.query(func.count(attribute)), filter)
            count = query.scalar()
            cache.set(key, count)
        return count

    def del_property_cache(self, prop: str) -> None:
        """
        Delete a property from the property cache.

        :param prop: The property to delete
        """
        try:
            del self._property_cache[prop]
        except (AttributeError, KeyError):
            pass

    def serialize(self, **kwargs) -> None:
        """
        Serializes the object with the serializer assigned to the ``__serializer__``
        attribute. Takes the same kwargs that the ``__serializer__`` object does.
        """
        return self.__serializer__.serialize(self, **kwargs)

    @property
    def cache_key(self) -> str:
        """
        Default property for cache key which should be overridden if the
        cache key is not formatted with an ID column. If the cache key
        string for the model only takes an {id} param, then this function
        will suffice.

        :return:           The cache key of the model
        :raises NameError: If the model does not have a cache key
        """
        return self.create_cache_key(self.primary_key)
