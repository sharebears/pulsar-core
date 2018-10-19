from collections import defaultdict
from enum import Enum
from typing import Dict, List, Set, Tuple, Union

import flask
from voluptuous import Invalid

from core import APIException
from core.permissions import Permissions
from core.permissions.models import SecondaryClass, UserPermission
from core.users.models import User


def PermissionsList(perm_list: List[str]) -> List[str]:
    """
    Validates that every permission in the list is a valid permission.

    :param perm_list: A list of permissions encoded as ``str``

    :return:          The inputted perm_list
    :raises Invalid:  If a permission in the list isn't valid or input isn't a list
    """
    invalid = []
    if isinstance(perm_list, list):
        for perm in perm_list:
            if not Permissions.is_valid_permission(perm):
                invalid.append(perm)
    else:
        raise Invalid('Permissions must be in a list,')
    if invalid:
        raise Invalid(f'The following permissions are invalid: {", ".join(invalid)},')
    return perm_list


def PermissionsListOfUser(perm_list: List[str]) -> List[str]:
    """
    Takes a list of items and asserts that all of them are in the permissions list of
    a user.

    :param perm_list: A list of permissions encoded as ``str``

    :return:          The input perm_list
    :raises Invalid:  If the user does not have a permission in the list
    """
    if isinstance(perm_list, list):
        for perm in perm_list:
            if not flask.g.user.has_permission(perm):
                break
        else:
            return perm_list
    raise Invalid('permissions must be in the user\'s permissions list')


class PermissionsDict:
    """
    Validates that a dictionary contains valid permission name keys
    and has boolean values. The available permissions can be restricted
    to the BASIC_PERMISSIONS if a permission is passed. If the requesting
    user does not have that permission, they will be restricted to the
    BASIC_PERMISSIONS.
    """

    def __init__(self, restrict: Union[str, Enum] = None) -> None:
        self.restrict = restrict

    def __call__(self, permissions: dict) -> dict:
        """
        :param permissions:    Dictionary of permissions and booleans

        :return:               The input value
        :raises Invalid:       A permission name is invalid or a value isn't a bool
        """
        permissioned = self.restrict is None or flask.g.user.has_permission(self.restrict)
        if isinstance(permissions, dict):
            for perm_name, action in permissions.items():
                if not isinstance(action, bool):
                    raise Invalid('permission actions must be booleans')
                elif (not Permissions.is_valid_permission(perm_name, permissioned)
                      and not (permissioned and action is False)):
                    # Do not disallow removal of non-existent permissions.
                    raise Invalid(f'{perm_name} is not a valid permission')
        else:
            raise Invalid('input value must be a dictionary')
        return permissions


def check_permissions(user: User,  # noqa: C901 (McCabe complexity)
                      permissions: Dict[str, bool]) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    The abstracted meat of the permission checkers. Takes the input and
    some model-specific information and returns permission information.

    :param user:        The recipient of the permission changes
    :param permissions: A dictionary of permission changes, with permission name
                        and boolean (True = Add, False = Remove) key value pairs
    :param perm_model:  The permission model to be checked
    :param perm_attr:   The attribute of the user classes which represents the permissions
    """
    add: Set[str] = set()
    ungrant: Set[str] = set()
    delete: Set[str] = set()
    errors: Dict[str, Set[str]] = defaultdict(set)

    uc_permissions: Set[str] = set(user.user_class_model.permissions)
    for class_ in SecondaryClass.from_user(user.id):
        uc_permissions |= set(class_.permissions)
    custom_permissions: Dict[str, bool] = UserPermission.from_user(user.id)

    for perm, active in permissions.items():
        if active is True:
            if perm in custom_permissions:
                if custom_permissions[perm] is False:
                    delete.add(perm)
                    add.add(perm)
            elif perm not in uc_permissions:
                add.add(perm)
            if perm not in add.union(delete):
                errors['add'].add(perm)
        else:
            if perm in custom_permissions and custom_permissions[perm] is True:
                delete.add(perm)
            if perm in uc_permissions:
                ungrant.add(perm)
            if perm not in delete.union(ungrant):
                errors['delete'].add(perm)

    if errors:
        message = []
        if 'add' in errors:
            message.append(f'The following permissions could not be added: '
                           f'{", ".join(errors["add"])}.')
        if 'delete' in errors:
            message.append(f'The following permissions could not be deleted: '
                           f'{", ".join(errors["delete"])}.')
        raise APIException(' '.join(message))

    return add, ungrant, delete
