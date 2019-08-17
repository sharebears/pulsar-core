import json

import flask
import pytest
from voluptuous import Invalid

from conftest import add_permissions, check_dupe_in_list, check_json_response
from core import APIException, db
from core.users.models import User
from core.validators import (
    PermissionsDict,
    PermissionsList,
    PermissionsListOfUser,
    check_permissions,
)


def test_PermissionsList(app, authed_client):
    permissions = ['users_change_password', 'permissions_modify']
    assert permissions == PermissionsList(permissions)


@pytest.mark.parametrize(
    'permissions, error',
    [
        (
            ['sample_one', 'sample_two'],
            'The following permissions are invalid: sample_one, sample_two,',
        ),
        (False, 'Permissions must be in a list,'),
    ],
)
def test_PermissionsListfailure(app, authed_client, permissions, error):
    with pytest.raises(Invalid) as e:
        PermissionsList(permissions)
    assert str(e.value) == error


def test_PermissionsListOfUser(app, authed_client):
    permissions = ['sample_one', 'sample_two']
    add_permissions(app, *permissions)
    assert permissions == PermissionsListOfUser(permissions)


def test_PermissionsListOfUser_failure(app, authed_client):
    permissions = ['sample_one', 'sample_two']
    add_permissions(app, 'sample_one', 'sample_three')
    with pytest.raises(Invalid) as e:
        PermissionsListOfUser(permissions)
    assert (
        str(e.value) == 'permissions must be in the user\'s permissions list'
    )


@pytest.mark.parametrize(
    'permissions', [['samp_perm_four', 'nonexistent_perm'], False]
)
def test_PermissionsListOfUser_error(app, authed_client, permissions):
    @app.route('/test_permissions_error', methods=['POST'])
    def test_permissions_error():
        with pytest.raises(Invalid):
            data = json.loads(flask.request.get_data())
            PermissionsListOfUser(data['permissions'])
        return flask.jsonify('completed')

    response = authed_client.post(
        '/test_permissions_error',
        data=json.dumps({'permissions': permissions}),
        content_type='application/json',
    )
    check_json_response(response, 'completed')


def test_PermissionsDict():
    permissions = {
        'permissions_modify': True,
        'invites_view': True,
        'fake_perm': False,
    }
    assert permissions == PermissionsDict().__call__(permissions)


@pytest.mark.parametrize(
    'permissions, expected',
    [
        (
            {'users_change_password': 'false', 'invites_view': True},
            'permission actions must be booleans',
        ),
        (
            {'change_wasspord': True, 'invites_view': False},
            'change_wasspord is not a valid permission',
        ),
        ('not-a-dict', 'input value must be a dictionary'),
    ],
)
def test_PermissionsDict_failure(permissions, expected):
    with pytest.raises(Invalid) as e:
        PermissionsDict().__call__(permissions)
    assert str(e.value) == expected


@pytest.mark.parametrize(
    'permissions, expected',
    [
        (
            {'sample_one': False, 'sample_two': False, 'sample_four': False},
            {
                'add': [],
                'ungrant': ['sample_four'],
                'delete': ['sample_one', 'sample_two'],
            },
        ),
        (
            {'sample_six': True},
            {'add': ['sample_six'], 'ungrant': [], 'delete': []},
        ),
        (
            {'sample_three': True},
            {
                'add': ['sample_three'],
                'ungrant': [],
                'delete': ['sample_three'],
            },
        ),
        (
            {'shared_perm': False},
            {'add': [], 'ungrant': ['shared_perm'], 'delete': ['shared_perm']},
        ),
    ],
)
def test_check_permission(app, authed_client, permissions, expected):
    add_permissions(app, 'sample_one', 'sample_two', 'shared_perm')
    db.engine.execute(
        """INSERT INTO users_permissions (user_id, permission, granted)
                      VALUES (1, 'sample_three', 'f')"""
    )
    db.engine.execute(
        """UPDATE user_classes
                      SET permissions = '{"sample_four", "sample_five"}'
                      WHERE name = 'User'"""
    )
    db.engine.execute(
        """UPDATE secondary_classes SET permissions = '{"shared_perm"}'
                      WHERE name = 'FLS'"""
    )
    add, ungrant, delete = check_permissions(User.from_pk(1), permissions)
    for li in [add, ungrant, delete]:
        check_dupe_in_list(li)
    assert set(add) == set(expected['add'])
    assert set(ungrant) == set(expected['ungrant'])
    assert set(delete) == set(expected['delete'])


@pytest.mark.parametrize(
    'permissions, error',
    [
        (
            {
                'sample_one': False,
                'sample_two': False,
                'sample_three': False,
                'non_existent': False,
            },
            ['deleted', 'sample_three', 'non_existent'],
        ),
        (
            {'sample_four': True, 'sample_one': True},
            ['added', 'sample_four', 'sample_one'],
        ),
    ],
)
def test_check_permission_error(app, authed_client, permissions, error):
    add_permissions(app, 'sample_one', 'sample_two')
    db.engine.execute(
        """INSERT INTO users_permissions (user_id, permission, granted)
                      VALUES (1, 'sample_three', 'f')"""
    )
    db.engine.execute(
        """UPDATE user_classes
                      SET permissions = '{"sample_four", "sample_five"}'
                      WHERE name = 'User'"""
    )
    with pytest.raises(APIException) as e:
        check_permissions(User.from_pk(1), permissions)
    assert all(w in e.value.message for w in error)
