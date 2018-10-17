import flask
import pytest

from conftest import add_permissions, check_json_response
from core.utils import access_other_user, assert_permission, assert_user


@pytest.mark.parametrize(
    'endpoint, result', [
        ('1/sample_permission', True),
        ('2/sample_permission', True),
        ('1', True),
        ('1/nonexistent_permission', True),
        ('2/nonexistent_permission', False),
        ('2', False),
    ])
def test_assert_user(app, authed_client, endpoint, result):
    add_permissions(app, 'sample_permission')

    @app.route('/assert_user_test/<int:user_id>')
    @app.route('/assert_user_test/<int:user_id>/<permission>')
    def assert_user_test(user_id, permission=None):
        assert result == bool(assert_user(user_id, permission))
        return flask.jsonify('completed')

    response = authed_client.get(f'/assert_user_test/{endpoint}')
    check_json_response(response, 'completed')


@pytest.mark.parametrize(
    'permission, masquerade, expected', [
        ('sample_perm_one', False, 'Endpoint reached.'),
        ('not_a_real_perm', True, 'Resource does not exist.'),
        ('not_a_real_perm', False,
         'You do not have permission to access this resource.'),
    ])
def test_assert_permission(app, authed_client, permission, masquerade, expected):
    @app.route('/test_assert_perm')
    def assert_perm():
        assert_permission(permission, masquerade=masquerade)
        return flask.jsonify('Endpoint reached.')

    response = authed_client.get('/test_assert_perm')
    check_json_response(response, expected)


def test_access_other_user_but_same_user(app, authed_client):
    @app.route('/test_access')
    @access_other_user('non-existent-perm')
    def test_access(user):
        assert user.id == 1
        return flask.jsonify('Endpoint reached.')

    response = authed_client.get('/test_access', query_string={'user_id': 1})
    check_json_response(response, 'Endpoint reached.')


def test_access_other_user(app, authed_client):
    @app.route('/test_access')
    @access_other_user('sample_perm_one')
    def test_access(user):
        assert user.id == 2
        return flask.jsonify('Endpoint reached.')

    response = authed_client.get('/test_access', query_string={'user_id': 2})
    check_json_response(response, 'Endpoint reached.')


def test_access_other_user_malformed(app, authed_client):
    @app.route('/test_access')
    @access_other_user('sample_perm_one')
    def test_access(user):
        assert user.id == 2
        return flask.jsonify('Endpoint reached.')

    response = authed_client.get('/test_access', query_string={'user_id': 'abc'})
    check_json_response(response, 'User ID must be an integer.')


def test_access_other_user_fail(app, authed_client):
    @app.route('/test_access')
    @access_other_user('nonexistent_perm')
    def test_access_user(user):
        return flask.jsonify('Endpoint reached.')

    response = authed_client.get('/test_access', query_string={'user_id': 2})
    check_json_response(response, 'You do not have permission to access this resource.')
