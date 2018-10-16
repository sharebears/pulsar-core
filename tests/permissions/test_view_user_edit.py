import json

import pytest

from conftest import add_permissions, check_json_response
from core import db


def test_get_all_permissions(app, authed_client):
    add_permissions(app, 'permissions_modify')
    response = authed_client.get('/permissions')
    data = json.loads(response.get_data())['response']
    assert 'permissions' in data
    assert all(perm in data['permissions'] for perm in [
        'permissions_modify',
        'invites_view',
        'site_no_ip_history',
        ])
    assert all(len(perm) <= 32 for perm in data['permissions'])


def test_user_class_permissions(app, authed_client):
    add_permissions(app, 'invites_view')
    db.engine.execute(
        """UPDATE user_classes SET permissions = '{"permissions_modify"}'
        WHERE name = 'User'
        """)
    response = authed_client.get('/permissions')
    data = response.get_json()['response']
    assert all(perm in data['permissions'] for perm in [
        'permissions_modify',
        'invites_view',
        'userclasses_modify',
        ])


@pytest.mark.parametrize(
    'endpoint, method', [
        ('/permissions', 'GET'),
    ])
def test_route_permissions(authed_client, endpoint, method):
    db.engine.execute("DELETE FROM users_permissions")
    db.engine.execute("UPDATE user_classes SET permissions = '{}'")
    response = authed_client.open(endpoint, method=method)
    check_json_response(response, 'You do not have permission to access this resource.')
    assert response.status_code == 403


def test_get_all_permissions_permission(authed_client):
    db.engine.execute("DELETE FROM users_permissions")
    db.engine.execute("UPDATE user_classes SET permissions = '{}'")
    response = authed_client.get('/permissions', query_string={'all': 'true'})
    check_json_response(response, 'You do not have permission to access this resource.')
    assert response.status_code == 403
