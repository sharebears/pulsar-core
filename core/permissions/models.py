from typing import Dict, List

import flask
from sqlalchemy import select

from core import db
from core.mixins import ClassMixin, MultiPKMixin, Permission
from core.users.models import User

app = flask.current_app


class UserClass(db.Model, ClassMixin):
    __tablename__ = 'user_classes'
    __cache_key__ = 'user_class_{id}'
    __cache_key_all__ = 'user_classes'

    def has_users(self) -> bool:
        return bool(User.query.filter(User.user_class_id == self.id).first())


class SecondaryClass(db.Model, ClassMixin):
    __tablename__ = 'secondary_classes'
    __cache_key__ = 'secondary_class_{id}'
    __cache_key_all__ = 'secondary_classes'
    __cache_key_of_user__ = 'secondary_classes_users_{id}'

    @classmethod
    def from_user(cls, user_id: int) -> List['SecondaryClass']:
        return cls.get_many(
            key=cls.__cache_key_of_user__.format(id=user_id),
            expr_override=select(
                [secondary_class_assoc_table.c.secondary_class_id]).where(
                    secondary_class_assoc_table.c.user_id == user_id))

    def has_users(self) -> bool:
        return bool(db.session.execute(
            select([secondary_class_assoc_table.c.user_id]).where(
                secondary_class_assoc_table.c.secondary_class_id == self.id).limit(1)))


secondary_class_assoc_table = db.Table(
    'secondary_class_assoc', db.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), nullable=False),
    db.Column('secondary_class_id', db.Integer, db.ForeignKey('secondary_classes.id'),
              nullable=False))


class UserPermission(db.Model, MultiPKMixin):
    __tablename__ = 'users_permissions'
    _core_permissions_loaded = False

    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    permission: str = db.Column(db.String(36), primary_key=True)
    granted: bool = db.Column(db.Boolean, nullable=False, index=True, server_default='t')

    all_permissions = []

    @classmethod
    def from_user(cls,
                  user_id: int,
                  prefix: str = None) -> Dict[str, bool]:
        """
        Gets a dict of all custom permissions assigned to a user.

        :param user_id: User ID the permissions belong to
        :return:        Dict of permissions with the name as the
                        key and the ``granted`` value as the value
        """
        return {p.permission: p.granted for p in cls.query.filter(  # type: ignore
                    cls.user_id == user_id
                ).all() if not prefix or p.permission.startswith(prefix)}

    @classmethod
    def is_valid_permission(cls,
                            permission: str,
                            permissioned: bool = True) -> bool:
        if permissioned:
            return permission in cls.get_all_permissions()
        return permission in app.config['BASIC_PERMISSIONS']

    @classmethod
    def get_all_permissions(cls):
        if not cls._core_permissions_loaded:
            cls.all_permissions = Permission.get_all_permissions()
            cls._core_permissions_loaded = True
        return cls.all_permissions
