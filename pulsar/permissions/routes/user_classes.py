from copy import copy
from typing import Any, Dict, List

import flask
from voluptuous import All, Length, Optional, Schema

from pulsar import APIException, db
from pulsar.permissions.models import SecondaryClass, UserClass
from pulsar.utils import require_permission, validate_data
from pulsar.validators import BoolGET, PermissionsDict, PermissionsList

from . import bp

app = flask.current_app

VIEW_USER_CLASS_SCHEMA = Schema({
    'secondary': BoolGET,
    })


@bp.route('/user_classes/<int:user_class_id>', methods=['GET'])
@require_permission('modify_user_classes')
@validate_data(VIEW_USER_CLASS_SCHEMA)
def view_user_class(user_class_id: int,
                    secondary: bool = False) -> flask.Response:
    """
    View an available user class and its associated permission sets.
    Requires the ``list_user_classes`` permission.

    .. :quickref: UserClass; View a user class.

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": "<UserClass> or <SecondaryUserClass>"
       }

    :query boolean secondary: Whether or not to view a secondary or primary user class

    :statuscode 200: View successful
    """
    u_class: Any = SecondaryClass if secondary else UserClass
    return flask.jsonify(u_class.from_pk(user_class_id, _404=True))


@bp.route('/user_classes', methods=['GET'])
@require_permission('list_user_classes')
@validate_data(VIEW_USER_CLASS_SCHEMA)
def view_multiple_user_classes(secondary: bool = False) -> flask.Response:
    """
    View all available user classes and their associated permission sets.
    Requires the ``list_user_classes`` permission.

    .. :quickref: UserClass; View multiple user classes.

    **Example response**:

    .. parsed-literal::
       {
         "status": "success",
         "response": [
           "<UserClass or SecondaryUserClass>",
           "<UserClass or SecondaryUserClass>"
         ]
       }

    :query boolean secondary: Whether or not to view secondary or primary user classes

    :>json list response: A list of user classes

    :statuscode 200: View successful
    :statuscode 404: User class does not exist
    """
    return flask.jsonify({  # type: ignore
        'user_classes': UserClass.get_all(),
        'secondary_classes': SecondaryClass.get_all(),
        })


CREATE_USER_CLASS_SCHEMA = Schema({
    'name': All(str, Length(max=24)),
    'permissions': PermissionsList,
    Optional('secondary', default=False): BoolGET,
    }, required=True)


@bp.route('/user_classes', methods=['POST'])
@require_permission('modify_user_classes')
@validate_data(CREATE_USER_CLASS_SCHEMA)
def create_user_class(name: str,
                      permissions: List[str],
                      secondary: bool = False) -> flask.Response:
    """
    Create a new user class. Requires the ``modify_user_classes`` permission.

    .. :quickref: UserClass; Create new user class.

    **Example request**:

    .. parsed-literal::

       POST /user_classes HTTP/1.1

       {
         "name": "user_v2",
         "permissions": [
           "send_invites",
           "change_password"
         ]
       }

    **Example response**:

    .. parsed-literal::

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": "<UserClass> or <SecondaryUserClass>"
       }

    :json string name: Name of the user class
    :json list permissions: A list of permissions encoded as strings
    :json boolean secondary: Whether or not to create a secondary or primary class
        (Default False)

    :statuscode 200: User class successfully created
    :statuscode 400: User class name taken or invalid permissions
    """
    u_class: Any = SecondaryClass if secondary else UserClass
    return flask.jsonify(u_class.new(
        name=name,
        permissions=permissions))


@bp.route('/user_classes/<int:user_class_id>', methods=['DELETE'])
@require_permission('modify_user_classes')
def delete_user_class(user_class_id: int) -> flask.Response:
    """
    Create a new user class. Requires the ``modify_user_classes`` permission.

    .. :quickref: UserClass; Delete user class.

    **Example request**:

    .. parsed-literal::

       PUT /user_classes HTTP/1.1

       {
         "name": "user_v2"
       }

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": "UserClass user_v2 has been deleted."
       }

    :query boolean secondary: Whether or not to delete a secondary or primary user class

    :json string name: Name of the user class

    :statuscode 200: Userclass successfully deleted
    :statuscode 400: Unable to delete user class
    :statuscode 404: Userclass does not exist
    """
    # Determine secondary here because it's a query arg
    request_args = flask.request.args.to_dict()
    secondary = BoolGET(request_args['secondary']) if 'secondary' in request_args else False
    u_class: Any = SecondaryClass if secondary else UserClass

    user_class = u_class.from_pk(user_class_id, _404=True)
    if user_class.has_users():
        raise APIException(f'You cannot delete a {u_class.__name__} '
                           'while users are assigned to it.')

    response = f'{u_class.__name__} {user_class.name} has been deleted.'
    db.session.delete(user_class)
    db.session.commit()
    return flask.jsonify(response)


MODIFY_USER_CLASS_SCHEMA = Schema({
    'permissions': PermissionsDict(),
    Optional('secondary', default=False): BoolGET,
    }, required=True)


@bp.route('/user_classes/<int:user_class_id>', methods=['PUT'])
@require_permission('modify_user_classes')
@validate_data(MODIFY_USER_CLASS_SCHEMA)
def modify_user_class(user_class_id: int,
                      permissions: Dict[str, bool],
                      secondary: bool = False) -> flask.Response:
    """
    Modifies permissions for an existing user class.
    Requires the ``modify_user_classes`` permission.

    .. :quickref: UserClass; Modify existing user class.

    **Example request**:

    .. parsed-literal::

       PUT /user_classes/user HTTP/1.1

       {
         "permissions": {
           "send_invites": false,
           "change_password": true,
           "list_permissions": true
         }
       }

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": "<UserClass> or <SecondaryUserClass>"
       }

    :>json dict permissions: A dictionary of permissions to add/remove, with
        the permission name as the key and a boolean (True = add, False = remove)
        as the value.
    :>json boolean secondary: Whether or not to modify a secondary or primary user class

    :statuscode 200: Userclass successfully modified
    :statuscode 400: Permissions cannot be applied
    :statuscode 404: Userclass does not exist
    """
    u_class: Any = SecondaryClass if secondary else UserClass
    user_class = u_class.from_pk(user_class_id, _404=True)

    uc_perms = copy(user_class.permissions)
    to_add = {p for p, a in permissions.items() if a is True}
    to_delete = {p for p, a in permissions.items() if a is False}

    for perm in to_add:
        if perm in uc_perms:
            raise APIException(
                f'{u_class.__name__} {user_class.name} already has the permission {perm}.')
        uc_perms.append(perm)
    for perm in to_delete:
        if perm not in uc_perms:
            raise APIException(
                f'{u_class.__name__} {user_class.name} does not have the permission {perm}.')
        uc_perms.remove(perm)

    # Permissions don't update if list reference doesn't change.
    # (This is also why uc_perms was copied from user_class.permissions)
    user_class.permissions = uc_perms
    db.session.commit()
    return flask.jsonify(user_class)
