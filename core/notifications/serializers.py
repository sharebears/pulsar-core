from core.mixins import Attribute, Serializer
from core.notifications.permissions import NotificationPermissions


class NotificationSerializer(Serializer):
    id = Attribute(permission=NotificationPermissions.VIEW_OTHERS)
    user_id = Attribute(permission=NotificationPermissions.VIEW_OTHERS)
    type = Attribute(permission=NotificationPermissions.VIEW_OTHERS)
    time = Attribute(permission=NotificationPermissions.VIEW_OTHERS)
    contents = Attribute(permission=NotificationPermissions.VIEW_OTHERS)
    read = Attribute(permission=NotificationPermissions.VIEW_OTHERS)
