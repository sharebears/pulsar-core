import flask

from core import APIException
from core.utils import choose_user, require_permission
from core.notifications import TYPES
from core.notifications.models import Notification

from . import bp


@bp.route('/notifications', methods=['GET'])
@bp.route('/notifications/user/<int:user_id>', methods=['GET'])
@require_permission('view_notifications')
def view_notifications(user_id=None):
    """
    View all pending notifications for a user. This includes thread subscriptions,
    collage notifications, torrent notifications, and inbox messages.
    """
    user = choose_user(user_id, 'view_notifications_others')
    return flask.jsonify(Notification.get_all_unread(user.id))


@bp.route('/notifications/<type>', methods=['GET'])
@bp.route('/notifications/<type>/user/<int:user_id>', methods=['GET'])
@require_permission('view_notifications')
def view_notification_type(type, user_id=None):
    """
    View all pending notifications for a user. This includes thread subscriptions,
    collage notifications, torrent notifications, and inbox messages.
    """
    user = choose_user(user_id, 'view_notifications_others')
    if type in TYPES:
        return flask.jsonify(Notification.from_type(user.id, type))
    raise APIException(f'{type} is not a valid notification type.')
