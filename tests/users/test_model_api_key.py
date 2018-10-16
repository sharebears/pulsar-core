import pytest

from conftest import CODE_1, CODE_2, CODE_3, add_permissions, check_dictionary
from core import NewJSONEncoder
from core.users.models import APIKey


def hex_generator(_):
    return next(HEXES)


def test_new_key(app, client):
    raw_key, api_key = APIKey.new(2, '127.0.0.2', 'UA', False)
    assert len(raw_key) == 26
    assert api_key.ip == '127.0.0.2'
    assert api_key.user_id == 2


def test_api_key_collision(app, client, monkeypatch):
    # First four are the the id and csrf_token, last one is the 16char key.
    global HEXES
    HEXES = iter([CODE_2[:10], CODE_3[:10], CODE_1[:16]])
    monkeypatch.setattr('core.users.models.secrets.token_urlsafe', hex_generator)

    raw_key, api_key = APIKey.new(2, '127.0.0.2', 'UA', False)
    assert len(raw_key) == 26
    assert api_key.hash != CODE_2[:10]
    with pytest.raises(StopIteration):
        hex_generator(None)


def test_from_pk_and_check(app, client):
    api_key = APIKey.from_pk('abcdefghij')
    assert api_key.user_id == 1
    assert api_key.check_key(CODE_1)
    assert not api_key.check_key(CODE_2)


def test_from_pk_when_dead(app, client):
    api_key = APIKey.from_pk('1234567890', include_dead=True)
    assert api_key.user_id == 2
    assert api_key.check_key(CODE_2)


def test_api_key_permission(app, client):
    api_key = APIKey.from_pk('abcdefghij', include_dead=True)
    assert api_key.has_permission('sample_permission')
    assert not api_key.has_permission('not_a_permission')


def test_serialize_no_perms(app, client):
    api_key = APIKey.from_pk('abcdefghij')
    assert NewJSONEncoder().default(api_key) is None


def test_serialize_detailed(app, authed_client):
    add_permissions(app, 'api_keys_view_others')
    api_key = APIKey.from_pk('1234567890', include_dead=True)
    data = NewJSONEncoder().default(api_key)
    check_dictionary(data, {
        'hash': '1234567890',
        'user_id': 2,
        'ip': '0.0.0.0',
        'user_agent': None,
        'revoked': True,
        'permanent': False,
        'timeout': 3600,
        'permissions': [],
        })
    assert 'last_used' in data and isinstance(data['last_used'], int)


def test_serialize_self(app, authed_client):
    api_key = APIKey.from_pk('abcdefghij')
    data = NewJSONEncoder().default(api_key)
    check_dictionary(data, {
        'hash': 'abcdefghij',
        'user_id': 1,
        'ip': '0.0.0.0',
        'user_agent': None,
        'revoked': False,
        'permissions': ['sample_permission', 'sample_2_permission', 'sample_3_permission'],
        })
    assert 'last_used' in data and isinstance(data['last_used'], int)
