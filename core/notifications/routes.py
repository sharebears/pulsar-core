import flask
from voluptuous import All, In, Range, Schema

from core import APIException, db
from core.notifications.models import Notification
from core.utils import access_other_user, require_permission, validate_data
from core.users.models import User
from core.validators import BoolGET
from core.notifications.permissions import NotificationPermissions

from . import bp


@bp.route('/notifications', methods=['GET'])
@require_permission(NotificationPermissions.VIEW)
@access_other_user(NotificationPermissions.VIEW_OTHERS)
def view_notifications(user: User):
    """
    View all pending notifications for a user. This includes thread subscriptions,
    collage notifications, torrent notifications, and inbox messages. Requires the
    ``notifications_view`` permission. Viewing the notifications of another user
    requires the ``notifications_view_others`` permission.

    .. :quickref: Notification; View unread notifications.

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": {
           "notification type 1": [
             "<Notification>",
             "<Notification>"
           ],
           "notification type 2": [
             "<Notification>",
             "<Notification>"
           ]
         }
       }

    :>json dict response: A dictionary of notification types and lists of notifications

    :statuscode 200: Successfully viewed notifications.
    :statuscode 403: User does not have access to view notifications.
    """
    return flask.jsonify(Notification.get_all_unread(user.id))


VIEW_NOTIFICATION_SCHEMA = Schema({
    'page': All(int, Range(min=0, max=2147483648)),
    'limit': All(int, In((25, 50, 100))),
    'include_read': BoolGET
    })


@bp.route('/notifications/<type>', methods=['GET'])
@require_permission(NotificationPermissions.VIEW)
@validate_data(VIEW_NOTIFICATION_SCHEMA)
@access_other_user(NotificationPermissions.VIEW_OTHERS)
def view_notification_type(type: str,
                           user: User,
                           page: int = 1,
                           limit: int = 50,
                           include_read: bool = False):
    """
    View all pending notifications of a specific type. Requires the
    ``notifications_view`` permission. Viewing the notifications of
    another user requires the ``notifications_view_others`` permission.

    .. :quickref: Notification; View notifications of a type.

    **Example request**:

    .. parsed-literal::

       GET /notifications/type_1 HTTP/1.1

       {
         "page": 1,
         "limit": 50,
         "include_read": False
       }

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": [
           "<Notification>",
           "<Notification>"
         ]
       }

    :>json dict response: A list of notifications

    :statuscode 200: Successfully viewed notifications.
    :statuscode 400: Notification type is invalid.
    :statuscode 403: User does not have access to view notifications.
    """
    return flask.jsonify(Notification.from_type(user.id, type, include_read=include_read))


MODIFY_NOTIFICATION_SCHEMA = Schema({
    'read': bool,
    }, required=True)


@bp.route('/notifications', methods=['PUT'])
@bp.route('/notifications/<type>', methods=['PUT'])
@require_permission(NotificationPermissions.MODIFY)
@validate_data(MODIFY_NOTIFICATION_SCHEMA)
@access_other_user(NotificationPermissions.MODIFY_OTHERS)
def clear_notifications(read: bool,
                        user: User,
                        type: str = None):
    """
    Clear a user's notifications; optionally of a specific type. Requires the
    ``notifications_modify`` permission. Clearing another user's notifications
    requires the ``notifications_modify_others`` permission.

    .. :quickref: Notification; View notifications of a type.

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": "All notifications cleared."
       }

    :>json str response: Response message

    :statuscode 200: Successfully cleared notifications.
    :statuscode 403: User does not have permission to clear notifications.
    """
    if not read:
        raise APIException('You cannot set all notifications to unread.')
    Notification.update_many(
        pks=Notification.get_pks_from_type(user.id, type, include_read=False),
        update={'read': True})
    Notification.clear_cache_keys(user.id)
    return flask.jsonify(f'{"All" if not type else type} notifications cleared.')


@bp.route('/notifications/<int:id>', methods=['PUT'])
@require_permission(NotificationPermissions.MODIFY)
@validate_data(MODIFY_NOTIFICATION_SCHEMA)
def modify_notification(id: int, read: bool):
    """
    Change the read status of a notification. Requires the
    ``notifications_modify`` permission. Modifying another user's
    notifications requires the ``notifications_modify_others`` permission.

    .. :quickref: Notification; Flag notification as read/unread.

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": "Notification 1243 marked as read."
       }

    :>json str response: Response message

    :statuscode 200: Successfully modified notification.
    :statuscode 403: User does not have permission to modify notifications.
    :statuscode 404: Notification does not exist.
    """
    noti = Notification.from_pk(id, asrt=NotificationPermissions.MODIFY_OTHERS, error=True)
    noti.read = read
    db.session.commit()
    Notification.clear_cache_keys(noti.user_id, noti.type)
    return flask.jsonify(f'Notification {id} marked as {"read" if read else "unread"}.')
