import flask
from typing import List

bp = flask.Blueprint('notifications', __name__)

PERMISSIONS = [
    'view_notifications',
    'view_notifications_others',
    ]

TYPES: List[str] = []
