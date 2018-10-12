from typing import List, Dict

from sqlalchemy import and_
import flask

from core import db
from core.mixins import SinglePKMixin
from core.notifications.serializers import NotificationSerializer
from core.notifications import TYPES

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
    type: str = db.Column(db.String, nullable=False, index=True)
    contents: str = db.Column(db.Text, nullable=False)
    read: bool = db.Column(db.Boolean, nullable=False, server_default='f', index=True)

    @classmethod
    def new(cls,
            user_id: int,
            type: str,
            contents: str) -> 'Notification':
        return super()._new(user_id=user_id, type=type, contents=contents)

    @classmethod
    def get_all_unread(cls,
                       user_id: int,
                       limit: int = 25) -> Dict[str, List['Notification']]:
        return {t: cls.get_many(
            key=cls.__cache_key_of_user__.format(user_id=user_id, type=t),
            filter=and_(
                cls.user_id == user_id,
                cls.type == t,
                cls.read == 'f'
                ),
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
    def get_notification_counts(cls, user_id: int) -> Dict[str, int]:
        return {t: cls.count(
            key=cls.__cache_key_notification_count__.format(user_id=user_id, type=t),
            attribute=cls.id,
            filter=and_(
                cls.user_id == user_id,
                cls.type == t,
                cls.read == 'f'
                )) for t in TYPES}
