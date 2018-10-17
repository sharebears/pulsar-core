from enum import Enum
import flask
from itertools import chain
from typing import List

from core.permissions.routes import bp  # noqa

app = flask.current_app


class PermissionsEnum(Enum):
    """This class is used to track the permission subclasses."""
    pass


class Permissions:
    _core_permissions_loaded = False
    permission_regexes: dict = {
        'basic': [],
        'full': [],
        }

    @classmethod
    def is_valid_permission(cls,
                            permission: str,
                            permissioned: bool = True) -> bool:
        print('hello')
        if permissioned:
            if permission in cls.get_all_permissions():
                return True
            return any(r.match(permission) for r in chain(*cls.permission_regexes.values()))
        if permission in app.config['BASIC_PERMISSIONS']:
            return True
        return any(r.match(permission) for r in cls.permission_regexes['basic'])

    @classmethod
    def get_all_permissions(cls):
        if not cls._core_permissions_loaded:
            cls.all_permissions = cls._get_all_permissions()
            cls._core_permissions_loaded = True
        return cls.all_permissions

    @staticmethod
    def _get_all_permissions() -> List[str]:
        """
        Aggregate all the permissions in permission enum subclasses. Restrict all
        uses of this function to users with the `get_all_permissions` permission.
        Returns the list of aggregated permissions

        :return: The list of permissions
        """
        return list(chain([e.value for c in PermissionsEnum.__subclasses__() for e in c]))
