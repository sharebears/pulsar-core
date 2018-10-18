from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import flask
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.elements import BinaryExpression

from core import APIException, _403Exception, _404Exception, cache, db
from core.mixins.base import PKBase

SPK = TypeVar('SPK', bound='SinglePKMixin')


class SinglePKMixin(PKBase):
    """
    This is the primary mixin for most of pulsar's model classes. This adds caching and JSON
    serialization functionality to the base SQLAlchemy model. Methods belonging to the mixin
    automatically cache fetched results and attempt to access cached results before querying the
    database when fetching a model. If caching is desired, methods belonging to this mixin should
    be used.

    Subclasses are expected to assign a serializer to the model by setting the ``__serializer__``
    attribute to a ``Serializer`` class. When a model is serialized in an API response, the
    serializer object will be used to turn the model into JSON.
    """

    @classmethod
    def from_pk(cls: Type[SPK],
                pk: Union[str, int, None],
                *,
                include_dead: bool = False,
                _404: bool = False,
                error: bool = False,
                asrt: Union[str, Enum] = None) -> Optional[SPK]:
                # TODO fix response type, this is why we are static optional.
        """
        Default classmethod constructor to get an object by its PK ID.
        If the object has a deleted/revoked/expired column, it will compare a
        ``include_dead`` kwarg against it. This function first attempts to load
        an object from the cache by formatting its ``__cache_key__`` with the
        ID parameter, and executes a query if the object isn't cached.
        Can optionally raise a ``_404Exception`` if the object is not queried.

        :param id:             The primary key ID of the object to query for
        :param include_dead:   Whether or not to return deleted/revoked/expired objects
        :param error:          Whether or not to raise a _403Exception when the user cannot
                               access the object
        :param _404:           Whether or not to raise a _404Exception with the value of
                               _404 and the class name as the resource name if an object
                               is not found
        :param asrt:           Whether or not to check for ownership of the model or a permission.
                               Can be a boolean to purely check for ownership, or a permission
                               string which can override ownership and access the model anyways.

        :return:               The object corresponding to the given ID, if it exists
        :raises _404Exception: If ``_404`` is passed and an object is not found nor accessible
        """
        if pk:
            model: SPK = cls.from_cache(
                key=cls.create_cache_key(pk),
                query=cls.query.filter(getattr(cls, cls.get_primary_key()) == pk))
            if (model is not None
                    and model.can_access(asrt, error)
                    and (include_dead
                         or not cls.__deletion_attr__
                         or not getattr(model, cls.__deletion_attr__, False))):
                return model
        if _404:
            raise _404Exception(f'{cls.__name__} {pk}')
        return None

    @classmethod
    def from_query(cls: Type[SPK],
                   *,
                   key: str = None,
                   filter: BinaryExpression = None,
                   order: BinaryExpression = None) -> Optional[SPK]:
        """
        Function to get a single object from the database (via ``limit(1)``, ``query.first()``).
        Getting the object via the provided cache key will be attempted first; if
        it does not exist, then a query will be constructed with the other
        parameters. The resultant object (if exists) will be cached and returned.

        **The queried model must have a primary key column named ``id`` and a
        ``from_pk`` classmethod constructor.**

        :param key:    The cache key belonging to the object
        :param filter: A SQLAlchemy expression to filter the query with
        :param order:  A SQLAlchemy expression to order the query by

        :return:       The queried model, if it exists
        """
        cls_pk = cache.get(key) if key else None
        if not cls_pk or not isinstance(cls_pk, int):
            query = cls._construct_query(cls.query, filter, order)
            model = query.first()
            if model:
                if not cache.has(model.cache_key):
                    cache.cache_model(model)
                if key:
                    cache.set(key, model.primary_key)
                return model
            return None
        return cls.from_pk(cls_pk)

    @classmethod
    def get_many(cls: Type[SPK],
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
                 expr_override: BinaryExpression = None) -> List[SPK]:
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
            pks = cls.get_pks_of_many(key, filter, order, include_dead, expr_override)
        if reverse:
            pks.reverse()
        if page is not None and limit is not None:
            all_next_pks = pks[(page - 1) * limit:]
            pks, extra_pks = all_next_pks[:limit], all_next_pks[limit:]

        models: List[SPK] = []
        while not limit or len(models) < limit:
            if pks:
                cls.populate_models_from_pks(models, pks, filter)

            # Check permissions on the models and filter out unwanted ones.
            models = [m for m in models if m.can_access(asrt)]
            if required_properties:
                models = [m for m in models if all(
                    getattr(m, rp, False) for rp in required_properties)]

            # End pagination loop and return models.
            if limit is None or page or not extra_pks:
                break
            pks = extra_pks[:abs(limit - len(models))]
            extra_pks = extra_pks[abs(limit - len(models)):]
        return list(models)

    @classmethod
    def get_pks_of_many(cls,
                        key: str = None,
                        filter: BinaryExpression = None,
                        order: BinaryExpression = None,
                        include_dead: bool = False,
                        expr_override: BinaryExpression = None) -> List[Union[int, str]]:
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
                pks = [x[0] for x in db.session.execute(expr_override)]
            else:
                query = cls._construct_query(
                    db.session.query(getattr(cls, cls.get_primary_key())), filter, order)
                if not include_dead and cls.__deletion_attr__:
                    query = query.filter(getattr(cls, cls.__deletion_attr__) == 'f')
                pks = [x[0] for x in query.all()]
            if key:
                cache.set(key, pks)
        return pks

    @classmethod
    def populate_models_from_pks(cls,
                                 models: List[SPK],
                                 pks: List[Union[str, int]],
                                 filter: BinaryExpression = None) -> None:
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
            qry_models: Dict[Union[int, str], SPK] = {
                obj.primary_key: obj for obj in
                cls._construct_query(cls.query.filter(
                    getattr(cls, cls.get_primary_key()).in_(uncached_pks)),
                    filter).all()
                    }
            cache.cache_models(qry_models.values())  # type: ignore
            for pk in uncached_pks:
                if pk in qry_models:
                    models.append(qry_models[pk])

    @classmethod
    def is_valid(cls,
                 pk: Union[int, str, None],
                 error: bool = False) -> bool:
        """
        Check whether or not the object exists and isn't deleted.

        :param id:            The object ID to validate
        :param error:         Whether or not to raise an APIException on validation fail
        :return:              Validity of the object
        :raises APIException: If error param is passed and ID is not valid
        """
        obj = cls.from_pk(pk)
        if error and not obj:
            raise APIException(f'Invalid {cls.__name__} {cls.get_primary_key()}.')
        return obj is not None

    @classmethod
    def create_cache_key(cls, pk: Union[int, str]) -> str:
        """
        Populate the ``__cache_key__`` class attribute with the kwargs.

        :param kwargs:     The keywords that will be fed into the ``str.format`` function

        :return:           The cache key
        :raises NameError: If the cache key is undefined or improperly defined
        """
        if cls.__cache_key__:
            try:
                return cls.__cache_key__.format(**{cls.get_primary_key(): pk})
            except KeyError:
                pass
        raise NameError(  # pramga: no cover
            'The cache key is undefined or improperly defined in this model.')

    @classmethod
    def update_many(cls, *,
                    pks: List[Union[str, int]],
                    update: Dict[str, Any],
                    sychronize_session: bool = False) -> None:
        """
        Construct and execute a query affecting all objects with PKs in the
        list of PKs passed to this function. This is only meant to be used for
        models with an PK primary key and cache key formatted by PK.

        :param pks:                 The list of primary key PKs to update
        :param update:              The dictionary of column values to update
        :param synchronize_session: Whether or not to update the session after
                                    the query; should be True if the objects are
                                    going to be used after updating
        """
        if pks:
            db.session.query(cls).filter(
                    getattr(cls, cls.get_primary_key()).in_(pks)
                ).update(update, synchronize_session=sychronize_session)
            db.session.commit()
            cache.delete_many(*(cls.create_cache_key(pk) for pk in pks))

    def can_access(self,
                   permission: Union[str, Enum] = None,
                   error: bool = False) -> bool:
        """
        Determines whether or not the requesting user can access the following resource.
        If no permission is specified, any user can access the resource. If a permission is
        specified, then access is restricted to users with that permission or "ownership"
        of this object. Ownership is determined with the ``belongs_to_user`` method.

        :param permission: Permission to restrict access to
        :return:           Whether or not the requesting user can access the resource
        """
        access = (permission is None
                  or self.belongs_to_user()
                  or flask.g.user.has_permission(permission))
        if error and not access:
            raise _403Exception
        return access

    def belongs_to_user(self) -> bool:
        """
        Function to determine whether or not the model "belongs" to a user by comparing
        against flask.g.user This is meant to be overridden by subclasses, although, by default,
        if the model has a ``user_id`` column, it compares ``flask.g.user`` with that column.
        If that column does not exist, ``False`` will be returned by default.

        :return: Whether or not the object "belongs" to the user
        """
        return flask.g.user is not None and flask.g.user.id == getattr(self, 'user_id', False)

    @classmethod
    def get_primary_key(cls) -> str:
        """
        Get the name of the primary key attribute of the model.

        :return: The primary key
        """
        return inspect(cls).primary_key[0].name

    @property
    def primary_key(self) -> Union[int, str]:
        """
        :return: The value associated with the primary key of the model
        """
        return getattr(self, self.get_primary_key())
