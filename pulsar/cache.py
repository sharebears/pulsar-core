from flask_sqlalchemy import Model
from sqlalchemy.orm.session import make_transient_to_detached
from werkzeug.contrib.cache import RedisCache


class Cache(RedisCache):
    """
    A custom implementation of werkzeug's RedisCache.
    This modifies and adds a few functions to RedisCache.
    """

    def __init__(self):
        # Override the RedisCache params we don't need.
        pass

    def init_app(self, app):
        """Required flask extension method."""
        super().__init__(**app.config['REDIS_PARAMS'])

    def inc(self, key, delta=1, timeout=None):
        """
        Increment a cache key if it exists, otherwise create it
        and optionally set a timeout.

        :param str key: The cache key to increment
        :param int delta: How much to increment the cache key by
        :param int timeout: If the cache key is newly created,
            how long to persist the key for
        """
        value = super().inc(key, delta)
        if timeout and value == delta:
            self._client.expire(self.key_prefix + key, timeout)
        return value

    def ttl(self, key):
        """
        Return the time to live (time until expiry) for a cache key.

        :return: The seconds left until a key expires (``int``)
        """
        return self._client.ttl(self.key_prefix + key)

    def cache_model(self, model, timeout=None):
        """
        Cache a SQLAlchemy model. Does nothing when ``model`` is ``None``.

        :param Model model: The SQLAlchemy ``Model`` to cache
        :param int timeout: The number of seconds to persist the key for
        """
        if model:
            data = {}
            for attr in model.__table__.columns.keys():
                data[attr] = getattr(model, attr, None)
            self.set(model.cache_key, data, timeout or self.default_timeout)


class PulsarModel(Model):
    """
    This is a custom model for the pulsar project, which adds caching
    and JSON serialization methods to the base model. Subclasses are
    expected to define their serializable attributes and cache key
    template with the following class attributes. They are required
    if one wants to cache or serialize data for a model. There are three
    tiers of serializable attributes, to reflect the different attributes
    which may be requested for at different permission levels.

    * ``__cache_key__``
    * ``__serializable_attrs__``
    * ``__serializable_attrs_detailed__``
    * ``__serializable_attrs_very_detailed__``

    Typically ``__serializable_attrs__`` is viewable to anyone with permission
    to see the resource, ``__serializable_attrs_detailed__`` is viewable by
    owners of the resource or users with (user-level) elevated permissions,
    and ``__serilizable_attrs_very_detailed__`` is reserved for site
    staff.
    """

    @classmethod
    def from_cache(cls, key):
        """
        Check the cache for an instance of this model and attempt to load
        its attributes from the cache instead of from the database.
        If found, the object is merged into the database session and returned.

        :param str key: The cache key to get
        """
        from pulsar import db, cache
        data = cache.get(key)
        if data:
            # Validate that all attributes are cached.
            if cls._valid_data(data):
                obj = cls(**data)
                make_transient_to_detached(obj)
                obj = db.session.merge(obj, load=False)
                return obj
            cache.delete(key)
        return None

    @classmethod
    def _valid_data(cls, data):
        """
        Check the validity of data being passed to a function by making sure that
        all of its cacheable attributes are being loaded.

        :param dict data: The stored object data to validate

        :return: ``True`` if valid or ``False`` if invalid
        """
        for attr in cls.__table__.columns.keys():
            if attr not in data:
                return False
        return True

    def clear_cache(self):
        """Clear the cache key for this instance of a model."""
        from pulsar import cache
        cache.delete(self.cache_key)

    def to_dict(self, detailed=False, very_detailed=False):
        """
        Convert the model to a dictionary based on its defined serializable attributes.
        ``PulsarModel`` objects embedded in the dictionary or lists in the dictionary
        will be replaced with the result of their ``to_dict`` methods.

        :param bool detailed: Whether or not to include detailed serializable attributes
        :param bool very_detailed: Whether or not to include very detailed serializable attributes

        :return: The ``dict`` of serialized attributes
        """
        attrs = getattr(self, '__serializable_attrs__', [])
        if (detailed or very_detailed) and hasattr(self, '__serializable_attrs_detailed__'):
            attrs += self.__serializable_attrs_detailed__
        if very_detailed and hasattr(self, '__serializable_attrs_very_detailed__'):
            attrs += self.__serializable_attrs_very_detailed__

        return self._objects_to_dict(
            {attr: getattr(self, attr, None) for attr in attrs})

    def _objects_to_dict(self, dict_):
        """
        Iterate through all values inside a dictionary and "fix" a dictionary to be
        JSON serializable by applying the to_dict() function to all embedded models.

        :param dict dict_: The dictionary to iterate over and "fix"

        :return: The "fixed" ``dict``
        """
        for k, v in dict_.items():
            if isinstance(v, dict):
                dict_[k] = self._objects_to_dict(v)
            if isinstance(v, list):
                v = [*v]  # Strip SQLA InstrumentedList
                for i, v2 in enumerate(v):
                    if isinstance(v2, PulsarModel):
                        v[i] = v2.to_dict()
                    elif isinstance(v2, dict):
                        v[i] = self._objects_to_dict(v2)
                dict_[k] = v
            elif isinstance(v, PulsarModel):
                dict_[k] = v.to_dict()

        return dict_
