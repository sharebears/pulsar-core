from enum import Enum


class NotificationPermissions(Enum):
    VIEW = 'notifications_view'
    VIEW_OTHERS = 'notifications_view_others'
    MODIFY = 'notifications_modify'
    MODIFY_OTHERS = 'notifications_modify_others'
