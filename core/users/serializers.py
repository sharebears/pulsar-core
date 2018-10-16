from core.mixins import Attribute, Serializer


class UserSerializer(Serializer):
    id = Attribute()
    username = Attribute()
    enabled = Attribute()
    user_class = Attribute()
    secondary_classes = Attribute()
    uploaded = Attribute()
    downloaded = Attribute()
    email = Attribute(permission='users_moderate')
    locked = Attribute(permission='users_moderate')
    invites = Attribute(permission='users_moderate')
    inviter = Attribute(permission='users_moderate', self_access=False, nested=False)
    api_keys = Attribute(permission='users_moderate', nested=False)
    basic_permissions = Attribute(permission='users_moderate', self_access=False, nested=False)
    permissions = Attribute(permission='users_moderate_advanced', nested=False)


class InviteSerializer(Serializer):
    code = Attribute(permission='invites_view_others')
    email = Attribute(permission='invites_view_others')
    time_sent = Attribute(permission='invites_view_others')
    expired = Attribute(permission='invites_view_others')
    invitee = Attribute(permission='invites_view_others')
    from_ip = Attribute(permission='invites_view_others', self_access=False)
    inviter = Attribute(permission='invites_view_others', nested=False, self_access=False)


class APIKeySerializer(Serializer):
    hash = Attribute(permission='api_keys_view_others')
    user_id = Attribute(permission='api_keys_view_others')
    last_used = Attribute(permission='api_keys_view_others')
    ip = Attribute(permission='api_keys_view_others')
    user_agent = Attribute(permission='api_keys_view_others')
    revoked = Attribute(permission='api_keys_view_others')
    permanent = Attribute(permission='api_keys_view_others')
    timeout = Attribute(permission='api_keys_view_others')
    permissions = Attribute(permission='api_keys_view_others')
