from typing import Any, List, Optional, Tuple, TypeVar, Union

from sqlalchemy import and_
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import BinaryExpression

from core import cache, db
from core.mixins.base import PKBase

MPK = TypeVar('MPK', bound='MultiPKMixin')


class MultiPKMixin(PKBase):
    """
    A model mixin for models with multiple primary keys, typically representative
    of many-to-many relational tables.
    """

    @classmethod
    def from_attrs(cls, **kwargs: Union[str, int]) -> Optional[MPK]:
        """
        Get an instance of the model from its attributes.

        :param kwargs: The attributes to query by
        :return:       An object matching the attributes
        """
        query = cls.query.filter(and_(*(getattr(cls, k) == v for k, v in kwargs.items())))
        if cls.__cache_key__:
            return cls.from_cache(key=cls.create_cache_key(kwargs), query=query)
        return query.scalar()

    @classmethod
    def get_col_from_many(cls,
                          *,
                          column: InstrumentedAttribute,
                          key: str = None,
                          filter: BinaryExpression = None,
                          order: BinaryExpression = None) -> List[Any]:
        """
        Get the values of a specific column from every row in the database.

        :param column: The desired column
        :param key:    A cache key to save the resultant list in
        :param filter: Filters to apply to the database query
        :param order:  How to order the values from the database query
        :return:       A list of values from the column
        """
        values = cache.get(key) if key else None
        if values is None:
            query = cls._construct_query(db.session.query(column), filter, order)
            values = [x[0] for x in query.all()]
            cache.set(key, values)
        return values

    @classmethod
    def create_cache_key(cls, attrs):
        return cls.__cache_key__.format(**{k: attrs[k] for k in cls.get_primary_keys()})

    @classmethod
    def get_primary_keys(cls) -> Tuple[str]:
        """
        Get the name of the primary key attribute of the model.

        :return: The primary key
        """
        return (m.name for m in inspect(cls).primary_key)

    @property
    def primary_key(self):
        return {k: getattr(self, k) for k in self.get_primary_keys()}
