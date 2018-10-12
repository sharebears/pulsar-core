import flask
from voluptuous import All, In, Range, Schema

from core import APIException, db
from core.notifications import TYPES
from core.notifications.models import Notification
from core.utils import choose_user, require_permission, validate_data
from core.validators import BoolGET

from . import bp


@bp.route('/notifications', methods=['GET'])
@bp.route('/notifications/user/<int:user_id>', methods=['GET'])
@require_permission('view_notifications')
def view_notifications(user_id: int = None):
    """
    View all pending notifications for a user. This includes thread subscriptions,
    collage notifications, torrent notifications, and inbox messages.
    """
    user = choose_user(user_id, 'view_notifications_others')
    return flask.jsonify(Notification.get_all_unread(user.id))


VIEW_NOTIFICATION_SCHEMA = Schema({
    'page': All(int, Range(min=0, max=2147483648)),
    'limit': All(int, In((25, 50, 100))),
    'include_read': BoolGET
    })


@bp.route('/notifications/<type>', methods=['GET'])
@bp.route('/notifications/<type>/user/<int:user_id>', methods=['GET'])
@require_permission('view_notifications')
@validate_data(VIEW_NOTIFICATION_SCHEMA)
def view_notification_type(type: str,
                           user_id: int = None,
                           page: int = 1,
                           limit: int = 50,
                           include_read: bool = False):
    """
    View all pending notifications for a user. This includes thread subscriptions,
    collage notifications, torrent notifications, and inbox messages.
    """
    user = choose_user(user_id, 'view_notifications_others')
    if type in TYPES:
        return flask.jsonify(Notification.from_type(user.id, type))
    raise APIException(f'{type} is not a valid notification type.')


@bp.route('/notifications/clear', methods=['PUT'])
@bp.route('/notifications/<type>/clear', methods=['PUT'])
@bp.route('/notifications/user/<int:user_id>/clear', methods=['PUT'])
@bp.route('/notifications/<type>/user/<int:user_id>/clear', methods=['PUT'])
@require_permission('notifications_clear')
def clear_notifications(type: str = None, user_id: int = None):
    user = choose_user(user_id, 'clear_notifications_others')
    Notification.update_many(
        pks=Notification.get_pks_from_type(user.id, type, include_read=False),
        update={'read': True})
    Notification.clear_cache_keys(user.id)
    return flask.jsonify(f'{"All" if not type else type} notifications cleared.')


MODIFY_NOTIFICATION_SCHEMA = Schema({
    'read': BoolGET,
    }, required=True)


@bp.route('/notifications/<int:id>', methods=['PUT'])
@validate_data(MODIFY_NOTIFICATION_SCHEMA)
def modify_notification(id: int, read: bool):
    noti = Notification.from_pk(id)
    setattr(noti, 'read', read)
    Notification.clear_cache_keys(noti.type)
    db.session.commit()
    return flask.jsonify(f'Notification {id} marked as {"read" if read else "unread"}.')
