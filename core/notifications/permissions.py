from core.mixins import Permission


class NotificationPermissions(Permission):
    VIEW = 'notifications_view'
    VIEW_OTHERS = 'notifications_view_others'
    MODIFY = 'notifications_modify'
    MODIFY_OTHERS = 'notifications_modify_others'
