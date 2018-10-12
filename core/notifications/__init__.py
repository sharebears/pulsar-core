from typing import List

import flask

bp = flask.Blueprint('notifications', __name__)

PERMISSIONS = [
    'notifications_view',
    'notifications_view_others',
    'notifications_clear',
    'notifications_clear_others',
    ]

TYPES: List[str] = []
