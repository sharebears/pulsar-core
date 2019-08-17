import json
from datetime import datetime, timedelta

import flask
import pytest

from conftest import (
    CODE_1,
    CODE_2,
    CODE_3,
    add_permissions,
    check_json_response,
)
from core import cache, db
from core.users.models import APIKey
from core.users.permissions import ApikeyPermissions
from core.utils import require_permission


def hex_generator(_):
    return next(HEXES)


@pytest.mark.parametrize(
    'key, expected',
    [
        ('abcdefghij', {'hash': 'abcdefghij', 'revoked': False}),
        ('1234567890', 'APIKey 1234567890 does not exist.'),
        ('notrealkey', 'APIKey notrealkey does not exist.'),
    ],
)
def test_view_api_key(app, authed_client, key, expected):
    add_permissions(app, ApikeyPermissions.VIEW)
    response = authed_client.get(f'/api_keys/{key}')
    check_json_response(response, expected)


def test_view_api_key_other(app, authed_client):
    add_permissions(app, ApikeyPermissions.VIEW, ApikeyPermissions.VIEW_OTHERS)
    response = authed_client.get(f'/api_keys/1234567890')
    check_json_response(response, {'hash': '1234567890', 'revoked': True})


def test_view_api_key_cached(app, authed_client):
    add_permissions(app, ApikeyPermissions.VIEW, ApikeyPermissions.VIEW_OTHERS)
    api_key = APIKey.from_pk('1234567890', include_dead=True)
    cache_key = cache.cache_model(api_key, timeout=60)

    response = authed_client.get(f'/api_keys/1234567890')
    check_json_response(response, {'hash': '1234567890', 'revoked': True})
    assert cache.ttl(cache_key) < 61


def test_view_all_keys(app, authed_client):
    add_permissions(app, ApikeyPermissions.VIEW)
    response = authed_client.get('/api_keys')
    data = response.get_json()['response']
    assert any(
        'hash' in api_key and api_key['hash'] == CODE_2[:10]
        for api_key in data
    )


def test_view_all_keys_cached(app, authed_client):
    add_permissions(app, ApikeyPermissions.VIEW)
    cache_key = APIKey.__cache_key_of_user__.format(user_id=1)
    cache.set(cache_key, ['abcdefghij', 'bcdefghijk'], timeout=60)

    response = authed_client.get('/api_keys')
    data = response.get_json()['response']
    assert any(
        'hash' in api_key and api_key['hash'] == CODE_2[:10]
        for api_key in data
    )
    assert cache.ttl(cache_key)


def test_view_empty_api_keys(app, authed_client):
    add_permissions(app, ApikeyPermissions.VIEW, ApikeyPermissions.VIEW_OTHERS)
    response = authed_client.get(
        '/api_keys', query_string={'user_id': 3, 'include_dead': False}
    )
    check_json_response(response, [], list_=True, strict=True)


def test_create_api_key(app, client, monkeypatch):
    global HEXES
    HEXES = iter(['a' * 8, 'a' * 16])
    monkeypatch.setattr(
        'core.users.models.secrets.token_urlsafe', hex_generator
    )
    response = client.post(
        '/api_keys',
        data=json.dumps({'username': 'user_one', 'password': '12345'}),
    )
    check_json_response(response, {'key': 'a' * 24})
    with pytest.raises(StopIteration):
        hex_generator(None)


def test_create_api_key_with_permissions(app, authed_client, monkeypatch):
    add_permissions(
        app, 'sample_permission', 'sample_perm_one', 'sample_perm_two'
    )
    global HEXES
    HEXES = iter(['a' * 8, 'a' * 16])
    monkeypatch.setattr(
        'core.users.models.secrets.token_urlsafe', hex_generator
    )
    authed_client.post(
        '/api_keys',
        data=json.dumps(
            {'permissions': ['sample_perm_one', 'sample_perm_two']}
        ),
        content_type='application/json',
    )
    key = APIKey.from_pk('a' * 8)
    assert key.has_permission('sample_perm_one')
    assert key.has_permission('sample_perm_two')
    assert not key.has_permission('sample_perm_three')


@pytest.mark.parametrize(
    'identifier, message',
    [
        ('abcdefghij', 'APIKey abcdefghij has been revoked.'),
        ('1234567890', 'APIKey 1234567890 is already revoked.'),
        (
            '\x02\xb0\xc0AZ\xf2\x99\x22\x8b\xdc',
            'APIKey \x02\xb0\xc0AZ\xf2\x99\x22\x8b\xdc does not exist.',
        ),
    ],
)
def test_revoke_api_key(app, authed_client, identifier, message):
    add_permissions(
        app, ApikeyPermissions.REVOKE, ApikeyPermissions.REVOKE_OTHERS
    )
    response = authed_client.delete(f'/api_keys/{identifier}')
    check_json_response(response, message)


def test_revoke_api_key_not_mine(app, authed_client):
    add_permissions(app, ApikeyPermissions.REVOKE)
    response = authed_client.delete('/api_keys/1234567890')
    check_json_response(response, 'APIKey 1234567890 does not exist.')


def test_revoke_all_api_keys(app, authed_client):
    add_permissions(app, ApikeyPermissions.REVOKE)
    response = authed_client.delete('/api_keys')
    check_json_response(response, 'All api keys have been revoked.')


def test_revoke_all_api_keys_other(app, authed_client):
    add_permissions(
        app, ApikeyPermissions.REVOKE, ApikeyPermissions.REVOKE_OTHERS
    )
    response = authed_client.delete('/api_keys', query_string={'user_id': 2})
    check_json_response(response, 'All api keys have been revoked.')


def test_view_resource_with_api_permission(app, client):
    add_permissions(
        app, 'sample_permission', 'sample_perm_one', 'sample_perm_two'
    )

    @app.route('/test_restricted_resource')
    @require_permission('sample_permission')
    def test_permission():
        return flask.jsonify('completed')

    response = client.get(
        '/test_restricted_resource',
        headers={'Authorization': f'Token abcdefghij{CODE_1}'},
    )
    check_json_response(response, 'completed')


def test_view_resource_with_user_permission(app, client):
    add_permissions(
        app, 'sample_permission', 'sample_perm_one', 'sample_perm_two'
    )

    @app.route('/test_restricted_resource')
    @require_permission('sample_permission')
    def test_permission():
        return flask.jsonify('completed')

    response = client.get(
        '/test_restricted_resource',
        headers={'Authorization': f'Token cdefghijkl{CODE_3}'},
    )
    check_json_response(response, 'completed')


def test_view_resource_with_user_restriction(app, client):
    @app.route('/test_restricted_resource')
    @require_permission('sample_2_permission')
    def test_permission():
        return flask.jsonify('completed')

    response = client.get(
        '/test_restricted_resource',
        headers={'Authorization': f'Token abcdefghij{CODE_1}'},
    )
    check_json_response(
        response, 'You do not have permission to access this resource.'
    )


def test_view_resource_with_api_key_restriction(app, client):
    add_permissions(
        app, 'sample_permission', 'sample_perm_one', 'sample_perm_two'
    )

    @app.route('/test_restricted_resource')
    @require_permission('sample_perm_one')
    def test_permission():
        return flask.jsonify('completed')

    response = client.get(
        '/test_restricted_resource',
        headers={'Authorization': f'Token abcdefghij{CODE_1}'},
    )
    check_json_response(
        response,
        'This APIKey does not have permission to access this resource.',
    )


def test_view_resource_with_expired_api_key(app, client):
    ak = APIKey.from_pk('abcdefghij')
    one_hour_ago = datetime.now() - timedelta(hours=1)
    ak.last_used = one_hour_ago
    db.session.commit()
    assert ak.revoked is False

    @app.route('/test_resource')
    def test_permission():
        return flask.jsonify('completed')

    response = client.get(
        '/test_resource',
        headers={'Authorization': f'Token abcdefghij{CODE_1}'},
    )
    check_json_response(response, 'Invalid authorization.')
    assert APIKey.from_pk('abcdefghij', include_dead=True).revoked is True


@pytest.mark.parametrize(
    'endpoint, method',
    [
        ('/api_keys/123', 'GET'),
        ('/api_keys', 'GET'),
        ('/api_keys/1234567890', 'DELETE'),
        ('/api_keys', 'DELETE'),
    ],
)
def test_route_permissions(app, authed_client, endpoint, method):
    response = authed_client.open(endpoint, method=method)
    check_json_response(
        response, 'You do not have permission to access this resource.'
    )
    assert response.status_code == 403
