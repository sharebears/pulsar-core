import flask
from flask_sqlalchemy import SQLAlchemy, event
from werkzeug import find_modules, import_string

from core.cache import cache, clear_cache_dirty
from core.exceptions import _401Exception  # noqa
from core.exceptions import (
    APIException,
    _312Exception,
    _403Exception,
    _404Exception,
    _405Exception,
    _500Exception,
)
from core.serializer import NewJSONEncoder

db = SQLAlchemy()


class Config:
    REQUIRE_INVITE_CODE = True
    INVITE_LIFETIME = 60 * 60 * 24 * 3  # 3 days
    RATE_LIMIT_AUTH_SPECIFIC = (50, 80)
    RATE_LIMIT_PER_USER = (80, 80)
    LOCKED_ACCOUNT_PERMISSIONS = {
        'view_staff_pm',
        'send_staff_pm',
        'resolve_staff_pm',
    }
    # These are permissions which can be manipulated by users with basic
    # user editing capibilities that do not have full permissioning powers.
    BASIC_PERMISSIONS = ['invites_send']


def init_app(app):
    db.init_app(app)
    cache.init_app(app)
    app.json_encoder = NewJSONEncoder
    event.listen(db.session, 'before_flush', clear_cache_dirty)

    with app.app_context():
        register_blueprints(app)
        register_error_handlers(app)


def register_blueprints(app: flask.Flask) -> None:
    # Every sub-view needs to be imported to populate the blueprint.
    # If this is not done, we will have empty blueprints.
    # If we register every module with the ``bp`` attribute normally,
    # we would have a lot of duplicate routes, which Werkzeug doesn't filter.
    for name in find_modules('core', recursive=True):
        if not name.endswith('conftest'):
            import_string(name)

    # Now import and register each blueprint. Since each blueprint
    # is defined in the package's __init__, we scan packages this time,
    # unlike the last.
    for name in find_modules('core', include_packages=True):
        if not name.endswith('conftest'):
            mod = import_string(name)
            if hasattr(mod, 'bp'):
                app.register_blueprint(mod.bp)

    # print(app.url_map)  # debug


def register_error_handlers(app: flask.Flask) -> None:
    app.register_error_handler(
        APIException, lambda err: (flask.jsonify(err.message), err.status_code)
    )
    app.register_error_handler(404, _404_handler)
    app.register_error_handler(405, _405_handler)
    app.register_error_handler(500, _500_handler)


def _404_handler(_) -> flask.Response:
    if not getattr(flask.g, 'user', False):
        return flask.jsonify(_401Exception().message), 401
    return flask.jsonify(_404Exception().message), 404


def _405_handler(_) -> flask.Response:
    return flask.jsonify(_405Exception().message), 405


def _500_handler(_) -> flask.Response:
    return flask.jsonify(_500Exception().message), 500
