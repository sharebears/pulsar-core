from core.mixins import Attribute, Serializer


class NotificationSerializer(Serializer):
    id = Attribute(permission='view_notifications_others')
    user_id = Attribute(permission='view_notifications_others')
    type = Attribute(permission='view_notifications_others')
    time = Attribute(permission='view_notifications_others')
    contents = Attribute(permission='view_notifications_others')
    read = Attribute(permission='view_notifications_others')
