from typing import Dict, List, Set

import flask
from sqlalchemy import and_, select

from core import db
from core.mixins import ClassMixin, MultiPKMixin
from core.users.models import User
from core.utils import get_all_permissions

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

    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    permission: str = db.Column(db.String(36), primary_key=True)
    granted: bool = db.Column(db.Boolean, nullable=False, index=True, server_default='t')

    @classmethod
    def from_user(cls, user_id: int) -> Dict[str, bool]:
        """
        Gets a dict of all custom permissions assigned to a user.

        :param user_id: User ID the permissions belong to
        :return:        Dict of permissions with the name as the
                        key and the ``granted`` value as the value
        """
        return {p.permission: p.granted for p in cls.query.filter(  # type: ignore
                    cls.user_id == user_id).all()}

    @classmethod
    def get_ungranted_from_user(cls, user_id: int) -> Set[str]:
        """
        Get all ungranted permission for a user.

        :param user_id: User ID to get the ungranted permission for
        :return:        A set of permissions
        """
        return {p.permission for p in cls.query.filter(and_(
            (cls.user_id == user_id),
            (cls.granted == 'f'))).all()}

    @classmethod
    def is_valid_permission(cls,
                            permission: str,
                            permissioned: bool = True) -> bool:
        permissions = get_all_permissions() if permissioned else cls.get_basic_permissions()
        return permission in permissions

    @classmethod
    def get_basic_permissions(cls):
        return app.config['BASIC_PERMISSIONS']
