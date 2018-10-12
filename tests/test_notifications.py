import pytest

from core import db
from core.notifications import TYPES
from core.notifications.models import Notification

TYPES.append('subscripple')
TYPES.append('quote')
TYPES.append('unreal')


@pytest.fixture(autouse=True)
def populate_db(client):
    db.engine.execute(
        """INSERT INTO notifications (id, user_id, type, contents, read) VALUES
        (1, 1, 'subscripple', 'A Subscribe!', 'f'),
        (2, 2, 'quote', 'A Quote!', 'f'),
        (3, 1, 'quote', 'A Quote!', 'f'),
        (4, 2, 'unreal', 'abcdef', 'f'),
        (5, 1, 'unreal', 'defgh', 't')
        """)
    db.engine.execute("ALTER SEQUENCE notifications_id_seq RESTART WITH 6")


def test_new_notification(client):
    noti = Notification.new(
        user_id=1,
        type='subscripple',
        contents='New Subscrippletion!')
    assert noti.id == 6
    assert noti.contents == 'New Subscrippletion!'
    assert noti.read is False


def test_get_notification_model(client):
    noti = Notification.from_pk(1)
    assert noti.id == 1
    assert noti.user_id == 1
    assert noti.type == 'subscripple'
    assert noti.contents == 'A Subscribe!'
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
