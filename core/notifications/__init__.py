import flask

bp = flask.Blueprint('notifications', __name__)

PERMISSIONS = [
    'notifications_view',
    'notifications_view_others',
    'notifications_modify',
    'notifications_modify_others',
    ]
