import json

import pytest

from core import db, cache, APIException
from core.notifications.models import Notification
from conftest import check_json_response, add_permissions


@pytest.fixture(autouse=True)
def populate_db(client):
    db.engine.execute(
        """INSERT INTO notifications_types (id, type) VALUES
        (1, 'subscripple'),
        (2, 'quote'),
        (3, 'unreal')
        """)
    db.engine.execute("ALTER SEQUENCE notifications_types_id_seq RESTART WITH 4")
    db.engine.execute(
        """INSERT INTO notifications (id, user_id, type_id, contents, read) VALUES
        (1, 1, 1, '{"contents": "A Subscribe!"}', 'f'),
        (2, 2, 2, '{"contents": "A Quote!"}', 'f'),
        (3, 1, 2, '{"contents": "A Quote!"}', 'f'),
        (4, 1, 2, '{"contents": "Another Quote!"}', 't'),
        (5, 2, 3, '{"contents": "abcdef"}', 'f'),
        (6, 1, 3, '{"contents": "defgh"}', 't')
        """)
    db.engine.execute("ALTER SEQUENCE notifications_id_seq RESTART WITH 7")


def test_new_notification(client):
    noti = Notification.new(
        user_id=1,
        type='subscripple',
        contents={'contents': 'New Subscrippletion!'})
    assert noti.id == 7
    assert noti.contents['contents'] == 'New Subscrippletion!'
    assert noti.read is False


def test_new_notification_new_type(client):
    noti = Notification.new(
        user_id=1,
        type='new_type',
        contents={'contents': 'New Type!'})
    assert noti.id == 7
    assert noti.contents['contents'] == 'New Type!'
    assert noti.type_id == 4
    assert noti.type == 'new_type'
    assert noti.read is False


def test_get_notification_model(client):
    noti = Notification.from_pk(1)
    assert noti.id == 1
    assert noti.user_id == 1
    assert noti.type == 'subscripple'
    assert noti.contents['contents'] == 'A Subscribe!'
    assert noti.read is False


def test_get_notification_counts(client):
    assert Notification.get_notification_counts(1) == {
        'subscripple': 1,
        'quote': 1,
        'unreal': 0,
        }


def test_get_unread_notifications(client):
    unread = Notification.get_all_unread(1)
    assert unread['subscripple'][0].id == 1
    assert len(unread['subscripple']) == 1
    assert unread['quote'][0].id == 3
    assert len(unread['quote']) == 1
    assert len(unread['unreal']) == 0


def test_get_notification_from_type(client):
    notis = Notification.from_type(1, 'quote')
    assert len(notis) == 1
    assert notis[0].id == 3


def test_get_notification_from_type_read(client):
    notis = Notification.from_type(1, 'unreal')
    assert len(notis) == 0


def test_get_notification_from_type_include_read(client):
    notis = Notification.from_type(1, 'unreal', include_read=True)
    assert len(notis) == 1


def test_get_notification_from_type_false(client):
    with pytest.raises(APIException) as e:
        Notification.from_type(1, 'bahaha', include_read=True)
    assert e.value.message == 'bahaha is not a notification type.'


def test_get_pks_from_type(client):
    pks = Notification.get_pks_from_type(1, 'subscripple')
    assert pks == [1]


def test_clear_cache_keys(client):
    ckey = Notification.__cache_key_notification_count__.format(user_id=1, type=1)
    cache.set(ckey, 100)
    Notification.clear_cache_keys(1, 'subscripple')
    assert not cache.has(ckey)


def test_clear_cache_keys_without_type(client):
    ckey = Notification.__cache_key_notification_count__.format(user_id=1, type=1)
    cache.set(ckey, 100)
    Notification.clear_cache_keys(1)
    assert not cache.has(ckey)


def test_clear_cache_keys_wrong_type(client):
    ckey = Notification.__cache_key_notification_count__.format(user_id=1, type='subscripple')
    cache.set(ckey, 100)
    with pytest.raises(APIException):
        Notification.clear_cache_keys(1, 'not_real_type')


def test_view_notifications(app, authed_client):
    add_permissions(app, 'notifications_view')
    response = authed_client.get('/notifications').get_json()['response']
    print(response)
    assert all(t in response for t in ['subscripple', 'quote', 'unreal'])
    assert not response['unreal']
    assert len(response['quote']) == 1 and response['quote'][0]['contents'] == {
        'contents': 'A Quote!'}


def test_view_notification_of_type(app, authed_client):
    add_permissions(app, 'notifications_view')
    response = authed_client.get('/notifications/quote').get_json()['response']
    assert len(response) == 1
    assert response[0]['type'] == 'quote'


def test_view_notification_of_type_include_read(app, authed_client):
    add_permissions(app, 'notifications_view')
    response = authed_client.get('/notifications/quote', query_string={
        'include_read': True}).get_json()['response']
    assert len(response) == 2
    assert all(response[i]['type'] == 'quote' for i in range(2))


def test_view_notification_of_nonexistent_type(app, authed_client):
    add_permissions(app, 'notifications_view')
    assert authed_client.get('/notifications/notreal').status_code == 400


def test_clear_notifications(app, authed_client):
    add_permissions(app, 'notifications_modify')
    assert authed_client.put(
        '/notifications', data=json.dumps({'read': True})).status_code == 200
    n = Notification.get_all_unread(1)
    assert all(len(v) == 0 for v in n.values())


def test_clear_notifications_type(app, authed_client):
    add_permissions(app, 'notifications_modify')
    assert authed_client.put(
        '/notifications/quote', data=json.dumps({'read': True})).status_code == 200
    n = Notification.get_all_unread(1)
    assert len(n['quote']) == 0
    assert len(n['subscripple']) == 1


def test_modify_notification(app, authed_client):
    add_permissions(app, 'notifications_modify')
    response = authed_client.put('/notifications/1', data=json.dumps({'read': True}))
    print(response.get_json())
    assert response.status_code == 200
    assert not len(Notification.get_all_unread(1)['subscripple'])
    assert len(Notification.get_all_unread(1)['quote']) == 1


@pytest.mark.parametrize(
    'endpoint, method', [
        ('/notifications', 'GET'),
        ('/notifications/type_1', 'GET'),
        ('/notifications', 'PUT'),
        ('/notifications/1', 'PUT'),
    ])
def test_route_permissions(authed_client, endpoint, method):
    response = authed_client.open(endpoint, method=method)
    check_json_response(response, 'You do not have permission to access this resource.')
    assert response.status_code == 403
