from core.mixins import Attribute, Serializer


class NotificationSerializer(Serializer):
    id = Attribute(permission='notifications_view_others')
    user_id = Attribute(permission='notifications_view_others')
    type = Attribute(permission='notifications_view_others')
    time = Attribute(permission='notifications_view_others')
    contents = Attribute(permission='notifications_view_others')
    read = Attribute(permission='notifications_view_others')
