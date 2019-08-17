import os
import sys
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum
from typing import Any, List

import flask
import pytest

import core
from core import cache, db
from core.test_data import CorePopulator
from core.users.models import User

POPULATORS: List[Any] = [CorePopulator]
PLUGINS: List[Any] = [core]


def create_app():
    class Config(
        *(plug.Config for plug in PLUGINS if hasattr(plug, 'Config'))
    ):
        pass

    app = flask.Flask(__name__)
    app.config.from_object(Config)
    app.config.from_pyfile('../tests/test_config.py')
    for plugin in PLUGINS:
        plugin.init_app(app)
    return app


HASHED_PASSWORD_1 = (
    'pbkdf2:sha256:50000$XwKgylbI$a4868823e7889553e3cb9f'
    'd922ad08f39c514c2f018cee3c07cd6b9322cc107d'
)  # 12345
HASHED_PASSWORD_2 = (
    'pbkdf2:sha256:50000$xH3qCWmd$a82cb27879cce1cb4de401'
    'fb8c171a42ca19bb0ca7b7e0ba7c6856087e25d3a8'
)  # abcdefg
HASHED_PASSWORD_3 = (
    'pbkdf2:sha256:50000$WnhbJYei$7af6aca3be169fb6a8b58b4'
    'fb666f0325bba59633eb4b4e292afeafbb9f89fa1'
)

CODE_1 = '1234567890abcdefghij1234'
CODE_2 = 'abcdefghijklmnopqrstuvwx'
CODE_3 = '234567890abcdefghij12345'
CODE_4 = 'zbjfeaofe38232r2qpfewfoo'

HASHED_CODE_1 = (
    'pbkdf2:sha256:50000$rAUuaX7W$01db64c80f4057c8fdcaddb13cb0'
    '01c712d7052717df3e38d647aae5eb1ab4f8'
)
HASHED_CODE_2 = (
    'pbkdf2:sha256:50000$CH2S6Ojr$71fdc1e523d2e6d063780392c83a'
    '6b6accbe0ea22bfe44c271e730001181f737'
)
HASHED_CODE_3 = (
    'pbkdf2:sha256:50000$DgIO3cu1$cdc9e2d1060c5f339e1cc7cf247d'
    'f32f49a8f94b4de45b2e149f4c00068ece00'
)


sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def check_json_response(response, expected, list_=False, strict=False):
    "Helper function to assert the JSON response matches the expected response."
    response_full = response.get_json()
    assert 'response' in response_full
    response = response_full['response']
    check_dictionary(response, expected, list_, strict)


def check_dictionary(response, expected, list_=False, strict=False):
    if strict:
        assert response == expected
    else:
        if list_:
            assert isinstance(response, list) and response
            response = response[0]

        if isinstance(expected, str):
            assert response == expected
        else:
            for key, value in expected.items():
                assert key in response and value == response[key]


def add_permissions(app_, *permissions):
    "Insert permissions into database for user_id 1 (authed user)."
    assert isinstance(app_, flask.Flask)
    permissions = [
        p if not isinstance(p, Enum) else p.value for p in permissions
    ]
    db.engine.execute(
        f"""INSERT INTO users_permissions (user_id, permission) VALUES
        (1, '"""
        + "'), (1, '".join(permissions)
        + "')"
    )


def check_dupe_in_list(list_):
    seen = set()
    for v in list_:
        if v in seen:
            return False
        seen.add(v)
    return True


@pytest.fixture(autouse=True, scope='session')
def db_create_tables():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.drop_all()


@pytest.fixture
def app(monkeypatch):
    app = create_app()
    with set_globals(app):
        with app.app_context():
            unpopulate_db()
            populate_db()
        yield app


@pytest.fixture
def client(app):
    with set_globals(app):
        with app.app_context():
            yield app.test_client()


@pytest.fixture
def authed_client(app, monkeypatch):
    monkeypatch.setattr(app, 'before_request_funcs', {})
    with set_globals(app):
        with app.app_context():
            user = User.from_pk(1)
    with set_globals(app):
        with set_user(app, user):
            with app.app_context():
                db.session.add(user)
                yield app.test_client()


@contextmanager
def set_globals(app_):
    def handler(sender, **kwargs):
        flask.g.cache_keys = defaultdict(set)
        flask.g.api_key = None
        flask.g.user_session = None
        if not hasattr(flask.g, 'user'):
            flask.g.user = None

    with flask.appcontext_pushed.connected_to(handler, app_):
        yield


@contextmanager
def set_user(app_, user):
    def handler(sender, **kwargs):
        flask.g.user = user

    with flask.appcontext_pushed.connected_to(handler, app_):
        yield


def populate_db():
    for p in POPULATORS:
        p.populate()
    cache.clear()


def unpopulate_db():
    for p in POPULATORS[::-1]:
        p.unpopulate()
