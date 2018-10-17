from functools import wraps
from typing import Callable, Union

import flask
from werkzeug.datastructures import MultiDict
from enum import Enum

from core import _312Exception, _401Exception, _403Exception, _404Exception, APIException

app = flask.current_app


def require_permission(permission: Union[str, Enum],
                       masquerade: bool = False) -> Callable:
    """
    Requires a user to have the specified permission to access the view function.

    :param permission:     The permission required to access the API endpoint
    :param masquerade:     Whether or not to disguise the failed view attempt as a 404

    :raises _403Exception: If the user does not exist or does not have enough
                           permission to view the resource. Locked accounts are
                           given a different message. This can be masqueraded as a 404
    :raises _403Exception: If an API Key is used and does not have enough permissions to
                           access the resource
    """
    permission = permission.value if isinstance(permission, Enum) else permission

    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        def new_function(*args, **kwargs) -> Callable:
            if not flask.g.user:
                raise _401Exception
            elif not flask.g.user.has_permission(permission):
                if flask.g.user.locked and not masquerade:
                    raise _312Exception(lock=True)
                raise _403Exception(masquerade=masquerade)
            elif flask.g.api_key and not flask.g.api_key.has_permission(permission):
                raise _403Exception(message='This APIKey does not have permission to '
                                    'access this resource.')
            return func(*args, **kwargs)
        return new_function
    return wrapper


def access_other_user(permission: Union[str, Enum]) -> Callable:
    """
    Takes a permission. The user_id is taken from the query string. If the user_id
    is specified, the user with that user id is fetched and then returned if the
    requesting user has the given permission.  Otherwise, the requester's user is
    returned. This decorator needs to be below a ``@require_permission`` decorated view.

    :param permission:     The permission needed to get the other user's user object.

    :return:               The chosen user
    :raises _403Exception: The requesting user does not have the specified permission
    :raises _404Exception: The requested user does not exist
    """
    permission = permission.value if isinstance(permission, Enum) else permission
    from core.users.models import User

    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        def new_function(*args, **kwargs) -> Callable:
            try:
                user_id = int(flask.request.args.to_dict().get('user_id', flask.g.user.id))
            except ValueError:
                raise APIException('User ID must be an integer.')

            # Remove user_id from the query string because validator will choke on it.
            flask.request.args = MultiDict(
                [(e, v) for e, v in flask.request.args.to_dict().items() if e != 'user_id'])
            if user_id == flask.g.user.id:
                return func(*args, user=flask.g.user, **kwargs)
            if permission:
                if not flask.g.user.has_permission(permission):
                    raise _403Exception
                elif flask.g.api_key and not flask.g.api_key.has_permission(permission):
                    raise _403Exception(message='This APIKey does not have permission to '
                                        'access this resource.')
            return func(*args, user=User.from_pk(user_id, _404=True), **kwargs)
        return new_function
    return wrapper


def assert_user(user_id: int,
                permission: Union[str, Enum] = None) -> bool:
    """
    Assert that a user_id belongs to the requesting user, or that
    the requesting user has a given permission.
    """
    permission = permission.value if isinstance(permission, Enum) else permission
    return (flask.g.user.id == user_id or flask.g.user.has_permission(permission))


def assert_permission(permission: Union[str, Enum],
                      masquerade: bool = False) -> None:
    "Assert that the requesting user has a permission, raise a 403 if they do not."
    permission = permission.value if isinstance(permission, Enum) else permission
    if not flask.g.user.has_permission(permission):
        if masquerade:
            raise _404Exception
        raise _403Exception
