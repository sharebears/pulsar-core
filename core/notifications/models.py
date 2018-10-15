from datetime import datetime
from itertools import chain
from typing import Dict, List, Union

import flask
from sqlalchemy import and_, func
from sqlalchemy.dialects.postgresql import JSONB

from core import APIException, cache, db
from core.mixins import SinglePKMixin
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
        return NotificationType.from_pk(self.type_id).type

    @classmethod
    def new(cls,
            user_id: int,
            type: str,
            contents: Dict[str, Union[Dict, str]]) -> 'Notification':
        User.is_valid(user_id, error=True)
        noti_type = NotificationType.from_type(type, create_new=True)
        return super()._new(
            user_id=user_id,
            type_id=noti_type.id,
            contents=contents)

    @classmethod
    def get_all_unread(cls,
                       user_id: int,
                       limit: int = 25) -> Dict[str, List['Notification']]:
        return {t.type: cls.get_many(
            key=cls.__cache_key_of_user__.format(user_id=user_id, type=t.id),
            filter=and_(cls.user_id == user_id, cls.type_id == t.id),
            limit=limit) for t in NotificationType.get_all()}

    @classmethod
    def from_type(cls,
                  user_id: int,
                  type: str,
                  page: int = 1,
                  limit: int = 50,
                  include_read: bool = False) -> List['Notification']:
        noti_type = NotificationType.from_type(type, error=True)
        return cls.get_many(
            key=cls.__cache_key_of_user__.format(user_id=user_id, type=noti_type.id),
            filter=and_(cls.user_id == user_id, cls.type_id == noti_type.id),
            page=page,
            limit=limit,
            include_dead=include_read)

    @classmethod
    def get_pks_from_type(cls,
                          user_id: int,
                          type: str,
                          include_read: bool = False):
        noti_type = NotificationType.from_type(type)
        if type:
            filter = and_(cls.user_id == user_id, cls.type_id == noti_type.id)
            cache_key = cls.__cache_key_of_user__.format(user_id=user_id, type=noti_type.id)
        else:
            filter = cls.user_id == user_id
            cache_key = cls.__cache_key_of_user__.format(user_id=user_id, type='all')

        return cls.get_pks_of_many(
            key=cache_key,
            filter=filter,
            include_dead=include_read)

    @classmethod
    def get_notification_counts(cls, user_id: int) -> Dict[str, int]:
        return {t.type: cls.count(
            key=cls.__cache_key_notification_count__.format(user_id=user_id, type=t),
            attribute=cls.id,
            filter=and_(
                cls.user_id == user_id,
                cls.type_id == t.id,
                cls.read == 'f'
                )) for t in NotificationType.get_all()}

    @classmethod
    def clear_cache_keys(cls, user_id: int, type=None) -> None:
        types = (
            [NotificationType.from_type(type, error=True)]
            if type else NotificationType.get_all())
        cache.delete_many(*chain(*chain([(
            cls.__cache_key_notification_count__.format(user_id=user_id, type=t.id),
            cls.__cache_key_of_user__.format(user_id=user_id, type=t.id)
            ) for t in types])))


class NotificationType(db.Model, SinglePKMixin):
    __tablename__ = 'notifications_types'
    __cache_key__ = 'notifications_type_{id}'
    __cache_key_id_of_type__ = 'notifications_type_{type}_id'
    __cache_key_all__ = 'notifications_type_all'

    id: int = db.Column(db.Integer, primary_key=True)
    type: str = db.Column(db.String, nullable=False, unique=True, index=True)

    @classmethod
    def from_type(cls,
                  type: str,
                  *,
                  create_new: bool = False,
                  error: bool = False) -> 'NotificationType':
        """
        Get the ID of the notification type, and if the type is not in the database,
        add it and return the new ID.

        :param type:           The notification type
        :param create_new:     Whether or not to create a new type with the given str
        :param error:          Whether or not to error if the type doesn't exist

        :return:               The notification ID
        :raises _404Exception: If error kwarg is passed and type doesn't exist
        """
        noti_type = cls.from_query(
            key=cls.__cache_key_id_of_type__.format(type=type),
            filter=cls.type == type)
        if noti_type:
            return noti_type
        elif create_new:
            return cls._new(type=type)
        elif error:
            raise APIException(f'{type} is not a notification type.')
        return None

    @classmethod
    def get_all(cls) -> List['NotificationType']:
        """
        Get all notification types in the database.

        :return: All notification type objects
        """
        return cls.get_many(key=cls.__cache_key_all__, order=cls.id, limit=None)
