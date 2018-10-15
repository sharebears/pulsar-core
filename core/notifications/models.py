from datetime import datetime
from itertools import chain
from typing import Dict, List, Union

import flask
from sqlalchemy import and_, func
from sqlalchemy.dialects.postgresql import JSONB

from core import cache, db
from core.mixins import SinglePKMixin
from core.notifications import TYPES
from core.notifications.serializers import NotificationSerializer
from core.users.models import User

app = flask.current_app


class Notification(db.Model, SinglePKMixin):
    __tablename__ = 'notifications'
    __serializer__ = NotificationSerializer
    __cache_key__ = 'notifications_{id}'
    __cache_key_of_user__ = 'notifications_user_{user_id}_{type}'
    __cache_key_notification_count__ = 'notifications_user_{user_id}_{type}_count'
    __deletion_attr__ = 'read'

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type_id: int = db.Column(
        db.Integer, db.ForeignKey('notifications_types.id'), nullable=False, index=True)
    time: datetime = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now())
    contents: str = db.Column(JSONB, nullable=False)
    read: bool = db.Column(db.Boolean, nullable=False, server_default='f', index=True)

    @property
    def type(self):
        return NotificationType.from_id(self.type_id).type

    @classmethod
    def new(cls,
            user_id: int,
            type: str,
            contents: Dict[str, Union[Dict, str]]) -> 'Notification':
        User.is_valid(user_id, error=True)
        noti_type = NotificationType.from_type(type)
        return super()._new(
            user_id=user_id,
            type_id=noti_type.id,
            contents=contents)

    @classmethod
    def get_all_unread(cls,
                       user_id: int,
                       limit: int = 25) -> Dict[str, List['Notification']]:
        return {t: cls.get_many(
            key=cls.__cache_key_of_user__.format(user_id=user_id, type=t),
            filter=and_(cls.user_id == user_id, cls.type == t),
            limit=limit) for t in TYPES}

    @classmethod
    def from_type(cls,
                  user_id: int,
                  type: str,
                  page: int = 1,
                  limit: int = 50,
                  include_read: bool = False) -> List['Notification']:
        return cls.get_many(
            key=cls.__cache_key_of_user__.format(user_id=user_id, type=type),
            filter=and_(cls.user_id == user_id, cls.type == type),
            page=page,
            limit=limit,
            include_dead=include_read)

    @classmethod
    def get_pks_from_type(cls,
                          user_id: int,
                          type: str,
                          include_read: bool = False):
        filter = cls.user_id == user_id
        if type:
            filter = and_(filter, cls.type == type)

        return cls.get_pks_of_many(
            key=cls.__cache_key_of_user__.format(user_id=user_id, type=type),
            filter=filter,
            include_dead=include_read)

    @classmethod
    def get_notification_counts(cls, user_id: int) -> Dict[str, int]:
        return {t: cls.count(
            key=cls.__cache_key_notification_count__.format(user_id=user_id, type=t),
            attribute=cls.id,
            filter=and_(
                cls.user_id == user_id,
                cls.type == t,
                cls.read == 'f'
                )) for t in TYPES}

    @classmethod
    def clear_cache_keys(cls, user_id: int, type=None) -> None:
        types = [type] if type else TYPES
        cache.delete_many(*chain(*chain([(
            cls.__cache_key_notification_count__.format(user_id=user_id, type=t),
            cls.__cache_key_of_user__.format(user_id=user_id, type=t)
            ) for t in types])))


class NotificationType(SinglePKMixin):
    __tablename__ = 'notifications_types'
    __cache_key__ = 'notifications_type_{id}'
    __cache_key_id_of_type__ = 'notifications_type_{type}_id'
    __cache_key_all__ = 'notifications_type_all'

    id: int = db.Column(db.Integer, primary_key=True)
    type: str = db.Column(db.String, nullable=False, unique=True, index=True)

    @classmethod
    def from_type(cls, type: str) -> 'NotificationType':
        """
        Get the ID of the notification type, and if the type is not in the database,
        add it and return the new ID.

        :param type: The notification type
        :return:     The notification ID
        """
        return cls.from_query(
            key=cls.__cache_key_id_of_type__.format(type=type),
            filter=cls.type == type
            ) or cls._new(type=type)

    @classmethod
    def get_all_types(cls) -> List['NotificationType']:
        """
        Get all notification types in the database.

        :return: All notification type objects
        """
        return cls.get_many(key=cls.__cache_key_all__, order=cls.id, limit=None)
