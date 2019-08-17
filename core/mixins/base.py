from collections import defaultdict
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from flask_sqlalchemy import BaseQuery, Model
from sqlalchemy import and_, func
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.session import make_transient_to_detached
from sqlalchemy.sql.elements import BinaryExpression

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
        permissions = [
            p if not isinstance(p, Enum) else p.value for p in permissions
        ]
        db.engine.execute(
            f"""INSERT INTO users_permissions (user_id, permission) VALUES
            (1, '"""
            + "'), (1, '".join(permissions)
            + "')"
        )


class PKBase(Model, BaseFunctionalityMixin):
    """
    A base class for the primary key mixin types. Contains their shared code and
    some attributes present in both.
    """

    __cache_key__: Optional[str] = None
    __deletion_attr__: Optional[str] = None
    __serializer__: Optional[Type['Serializer']] = None

    @classmethod
    def from_cache(cls, key: str, *, query: BaseQuery = None) -> Optional[PKB]:
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
    def _create_obj_from_cache(cls: Type[PKB], data: Any) -> Optional[PKB]:
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
        return (
            bool(data)
            and isinstance(data, dict)
            and set(data.keys()) == set(cls.__table__.columns.keys())
        )

    @classmethod
    def get_many(
        cls: Type[PKB],
        *,
        key: str = None,
        filter: BinaryExpression = None,
        order: BinaryExpression = None,
        required_properties: tuple = (),
        include_dead: bool = False,
        asrt: Union[str, Enum] = None,
        page: int = None,
        limit: Optional[int] = 50,
        reverse: bool = False,
        pks: List[Union[int, str]] = None,
        expr_override: BinaryExpression = None,
    ) -> List[PKB]:
        """
        An abstracted function to get a list of PKs from the cache with a cache key,
        and query for those IDs if the key does not exist. If the query needs to be ran,
        a list will be created from the first element in every returned tuple result, like so:
        ``[x[0] for x in cls.query.all()]``

        That list will be converted into models, using passed keyword arguments to modify
        which elements are included and which aren't. Pagination occurs here, although it is
        optional and ignored if neither page nor limit is set.

        :param key:                 The cache key to check (and return if present)
        :param filter:              A SQLAlchemy filter expression to be applied to the query
        :param order:               A SQLAlchemy order_by expression to be applied to the query
        :param required_properties: Properties required to validate to ``True``. This can break
                                    pagination (varying # on one page)
                                    for a retrieved item to be included in the returned list
        :param include_dead:        Whether or not to include deleted/revoked/expired models
        :param asrt:                Whether or not to check for ownership of the model or a
                                    permission. Can be a boolean to purely check for ownership,
                                    or a permission string which can override ownership and
                                    access the model anyways.
        :param page:                The page number of results to return
        :param limit:               The limit of results to return, defaults to 50 if page
                                    is set, otherwise infinite
        :param reverse:             Whether or not to reverse the order of the list
        :param ids:                 A list of previously-generated IDs to be used in lieu
                                    of re-generating the IDs
        :param expr_override:       If passed, this will override filter and order, and be
                                    called verbatim in a ``db.session.execute`` if the cache
                                    key does not exist

        :return:                    A list of objects matching the query specifications
        """
        extra_pks: List[Union[int, str]] = []
        if pks is None:
            pks = cls.get_pks_of_many(
                key, filter, order, include_dead, expr_override
            )
        if reverse:
            pks.reverse()
        if page is not None and limit is not None:
            all_next_pks = pks[(page - 1) * limit :]
            pks, extra_pks = all_next_pks[:limit], all_next_pks[limit:]

        models: List[PKB] = []
        while not limit or len(models) < limit:
            if pks:
                cls.populate_models_from_pks(models, pks, filter)

            # Check permissions on the models and filter out unwanted ones.
            models = [m for m in models if m.can_access(asrt)]
            if required_properties:
                models = [
                    m
                    for m in models
                    if all(getattr(m, rp, False) for rp in required_properties)
                ]

            # End pagination loop and return models.
            if limit is None or page or not extra_pks:
                break
            pks = extra_pks[: abs(limit - len(models))]
            extra_pks = extra_pks[abs(limit - len(models)) :]
        return list(models)

    @classmethod
    def get_pks_of_many(
        cls,
        key: str = None,
        filter: BinaryExpression = None,
        order: BinaryExpression = None,
        include_dead: bool = False,
        expr_override: BinaryExpression = None,
    ) -> List[Union[int, str]]:
        """
        Get a list of object IDs meeting query criteria. Fetching from the
        cache with the provided cache key will be attempted first; if the cache
        key does not exist then a query will be ran. Calls with ``include_dead=True`` are
        saved under a different cache key. ``include_dead`` does not affect the query results
        when passing ``expr_override``.

        :param key:                 The cache key to check (and return if present)
        :param filter:              A SQLAlchemy filter expression to be applied to the query
        :param order:               A SQLAlchemy order_by expression to be applied to the query
        :param include_dead:        Whether or not to include dead results in the IDs list
        :param expr_override:       If passed, this will override filter and order, and be
                                    called verbatim in a ``db.session.execute`` if the cache
                                    key does not exist

        :return:                    A list of IDs
        """
        key = f'{key}_incl_dead' if include_dead and key else key
        pks = cache.get(key) if key else None
        if not pks or not isinstance(pks, list):
            if expr_override is not None:
                pks = [
                    x[0] if len(x) == 1 else dict(x)
                    for x in db.session.execute(expr_override)
                ]
            else:
                primary_key = cls.get_primary_key()
                if isinstance(primary_key, list):
                    query = cls._construct_query(
                        db.session.query(
                            *(getattr(cls, k) for k in primary_key)
                        ),
                        filter,
                        order,
                    )
                else:
                    query = cls._construct_query(
                        db.session.query(getattr(cls, primary_key)),
                        filter,
                        order,
                    )
                if not include_dead and cls.__deletion_attr__:
                    query = query.filter(
                        getattr(cls, cls.__deletion_attr__) == 'f'
                    )
                pks = [
                    x[0] if len(x) == 1 else x._asdict() for x in query.all()
                ]
            if key:
                cache.set(key, pks)
        return pks

    @classmethod
    def populate_models_from_pks(
        cls,
        models: List[PKB],
        pks: List[Union[str, int]],
        filter: BinaryExpression = None,
    ) -> None:
        """
        Given a list of primary keys, fetch the objects corresponding to them from
        the cache and the database.

        :param models:  A list of models to append new ones to
        :param pks:     Primary keys of the objects to fetch
        :param filter:  What to filter out from the query for the objects
        """
        uncached_pks = []
        cached_dict = cache.get_dict(*(cls.create_cache_key(pk) for pk in pks))
        for i, (k, v) in zip(pks, cached_dict.items()):
            if v:
                models.append(cls._create_obj_from_cache(v))
            else:
                uncached_pks.append(i)

        if uncached_pks:
            if not isinstance(uncached_pks[0], dict):
                qry_models: Dict[Union[int, str], PKB] = {
                    obj.primary_key: obj
                    for obj in cls._construct_query(
                        cls.query.filter(
                            getattr(cls, cls.get_primary_key()).in_(
                                uncached_pks
                            )
                        ),
                        filter,
                    ).all()
                }
            else:
                uncached_pks_by_pk = defaultdict(list)
                for pk in uncached_pks:
                    for k, v in pk.items():
                        uncached_pks_by_pk[k].append(v)
                qry_models: Dict[Union[int, str], PKB] = {
                    tuple(obj.primary_key.values()): obj
                    for obj in cls._construct_query(
                        cls.query.filter(
                            and_(
                                getattr(cls, k).in_(uncached_pks_by_pk[k])
                                for k in uncached_pks_by_pk
                            )
                        ),
                        filter,
                    ).all()
                }
            cache.cache_models(qry_models.values())  # type: ignore
            for pk in uncached_pks:
                if isinstance(pk, dict):
                    pk = tuple(pk.values())
                if pk in qry_models:
                    models.append(qry_models[pk])

    @staticmethod
    def _construct_query(
        query: BaseQuery,
        filter: BinaryExpression = None,
        order: BinaryExpression = None,
    ) -> BaseQuery:
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
    def count(
        cls,
        *,
        key: str,
        attribute: InstrumentedAttribute,
        filter: BinaryExpression = None,
    ) -> int:
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
            query = cls._construct_query(
                db.session.query(func.count(attribute)), filter
            )
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
