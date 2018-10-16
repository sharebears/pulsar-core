import json

import pytest

from conftest import add_permissions, check_json_response
from core import db
from core.permissions.models import UserPermission
from core.users.models import User


def test_int_overflow(app, authed_client):
    add_permissions(app, 'users_moderate')
    response = authed_client.put('/users/1', data=json.dumps({
        'invites': 99999999999999999999999999,
        }))
    check_json_response(response, 'Invalid data: value must be at most 2147483648 (key "invites")')


def test_moderate_user(app, authed_client):
    add_permissions(app, 'users_moderate')
    response = authed_client.put('/users/2', data=json.dumps({
        'email': 'new@ema.il',
        'uploaded': 999,
        'downloaded': 998,
        'invites': 100,
        }))
    check_json_response(response, {
        'id': 2,
        'email': 'new@ema.il',
        'uploaded': 999,
        'downloaded': 998,
        })
    user = User.from_pk(2)
    assert user.email == 'new@ema.il'
    assert user.uploaded == 999


def test_moderate_user_incomplete(app, authed_client):
    add_permissions(app, 'users_moderate')
    response = authed_client.put('/users/2', data=json.dumps({
        'password': 'abcdefGHIfJK12#',
        }))
    check_json_response(response, {
        'id': 2,
        'email': 'user_two@puls.ar',
        'downloaded': 0,
        })
    user = User.from_pk(2)
    assert user.check_password('abcdefGHIfJK12#')
    assert user.email == 'user_two@puls.ar'


def test_moderate_user_not_found(app, authed_client):
    add_permissions(app, 'users_moderate')
    response = authed_client.put('/users/10', data=json.dumps({
        'email': 'new@ema.il',
        }))
    check_json_response(response, 'User 10 does not exist.')
    assert response.status_code == 404


def test_change_permissions(app, authed_client):
    add_permissions(app, 'users_change_password', 'userclasses_list', 'userclasses_modify')
    db.engine.execute("""INSERT INTO users_permissions (user_id, permission, granted)
                      VALUES (1, 'invites_send', 'f')""")
    db.engine.execute(
        """UPDATE user_classes
        SET permissions = '{"users_moderate", "users_moderate_advanced", "invites_view"}'""")

    response = authed_client.put('/users/1', data=json.dumps({
        'permissions': {
            'users_moderate': False,
            'users_change_password': False,
            'invites_view': False,
            'invites_send': True,
        }})).get_json()

    print(response['response'])
    assert set(response['response']['permissions']) == {
        'users_moderate_advanced', 'userclasses_modify', 'invites_send', 'userclasses_list'}

    u_perms = UserPermission.from_user(1)
    assert u_perms == {
        'userclasses_list': True,
        'userclasses_modify': True,
        'invites_send': True,
        'invites_view': False,
        'users_moderate': False,
        }


@pytest.mark.parametrize(
    'permissions, expected', [
        ({'invites_send': True, 'invites_view': False},
         'The following permissions could not be added: invites_send.'),
        ({'users_change_password': False, 'invites_send': False},
         'The following permissions could not be deleted: users_change_password.'),
        ({'legacy': False, 'invites_view': False},
         'legacy is not a valid permission.'),
    ])
def test_change_permissions_failure(app, authed_client, permissions, expected):
    add_permissions(app, 'users_moderate', 'users_moderate_advanced',
                    'invites_send', 'invites_view')
    db.engine.execute(
        """UPDATE user_classes SET permissions = '{"legacy"}'
        WHERE name = 'User'""")
    response = authed_client.put('/users/1', data=json.dumps({
        'permissions': permissions}))
    check_json_response(response, expected)


def test_change_permissions_restricted(app, authed_client):
    """Basic but not advanced permissions privileges."""
    add_permissions(app, 'users_moderate')
    response = authed_client.put('/users/1', data=json.dumps({
        'permissions': {'users_moderate': False}}))
    check_json_response(
        response, 'Invalid data: users_moderate is not a valid permission (key "permissions")')


@pytest.mark.parametrize(
    'endpoint, method', [
        ('/users/1', 'PUT'),
    ])
def test_route_permissions(app, authed_client, endpoint, method):
    response = authed_client.open(endpoint, method=method)
    check_json_response(response, 'You do not have permission to access this resource.')
    assert response.status_code == 403
