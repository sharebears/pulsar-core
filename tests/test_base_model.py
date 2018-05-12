import pytz
import pytest
from datetime import datetime
from conftest import add_permissions
from pulsar import cache, PulsarModel
from pulsar.models import User


def test_serialize_user_attributes(app, authed_client):
    user = User.from_id(2)
    data = user.to_dict()
    assert 'id' in data
    assert 'email' not in data
    assert 'inviter' not in data

    user = User.from_id(1)
    data = user.to_dict()
    assert 'id' in data
    assert 'email' in data
    assert 'inviter' not in data

    add_permissions(app, 'moderate_users')
    cache.delete(user.__cache_key_permissions__.format(id=2))

    user = User.from_id(2)
    data = user.to_dict()
    assert 'id' in data
    assert 'email' in data
    assert 'inviter' in data


def test_to_dict_plain(app, authed_client):
    dict_ = {
        'key1': {
            'subkey1': 'subval1',
            'subkey2': 'subval2',
            'subkey3': [
                'subval1',
                'subval2',
                {
                    'subkey1': 'subkey1',
                    'subkey2': 'subkey2',
                    'subkey3': 'subval3',
                },
            ],
        },
        'key2': 123,
    }
    assert dict_ == PulsarModel._objects_to_dict(dict_)


@pytest.mark.parametrize(
    'data, result', [
        ('not-a-dict', False),
        ({'id': 1, 'username': 'lights'}, False),
     ])
def test_is_valid_data(app, client, data, result):
    assert User._valid_data(data) is result


def test_serialization_of_datetimes(app, authed_client):
    time = datetime.utcnow().replace(tzinfo=pytz.utc)
    posix_time = int(time.timestamp())
    assert posix_time > 1500000000
    data = {
        'key': time,
        'key2': User.from_id(1),
        'key3': [time, time],
    }

    response = PulsarModel._objects_to_dict(data)
    assert response['key'] == posix_time
    assert 'id' in response['key2']
    assert 'username' in response['key2'] and response['key2']['username'] == 'lights'
    assert len(response['key3']) == 2
    print(response['key3'])
    assert all(k == posix_time for k in response['key3'])