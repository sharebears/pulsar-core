from core.mixins import Attribute, Serializer
from core.users.permissions import (
    ApikeyPermissions,
    InvitePermissions,
    UserPermissions,
)


class UserSerializer(Serializer):
    id = Attribute()
    username = Attribute()
    enabled = Attribute()
    user_class = Attribute()
    secondary_classes = Attribute()
    uploaded = Attribute()
    downloaded = Attribute()
    email = Attribute(permission=UserPermissions.MODERATE)
    locked = Attribute(permission=UserPermissions.MODERATE)
    invites = Attribute(permission=UserPermissions.MODERATE)
    inviter = Attribute(
        permission=UserPermissions.MODERATE, self_access=False, nested=False
    )
    api_keys = Attribute(permission=UserPermissions.MODERATE, nested=False)
    basic_permissions = Attribute(
        permission=UserPermissions.MODERATE, self_access=False, nested=False
    )
    permissions = Attribute(
        permission=UserPermissions.MODERATE_ADVANCED, nested=False
    )


class InviteSerializer(Serializer):
    code = Attribute(permission=InvitePermissions.VIEW_OTHERS)
    email = Attribute(permission=InvitePermissions.VIEW_OTHERS)
    time_sent = Attribute(permission=InvitePermissions.VIEW_OTHERS)
    expired = Attribute(permission=InvitePermissions.VIEW_OTHERS)
    invitee = Attribute(permission=InvitePermissions.VIEW_OTHERS)
    from_ip = Attribute(
        permission=InvitePermissions.VIEW_OTHERS, self_access=False
    )
    inviter = Attribute(
        permission=InvitePermissions.VIEW_OTHERS,
        nested=False,
        self_access=False,
    )


class APIKeySerializer(Serializer):
    hash = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    user_id = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    last_used = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    ip = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    user_agent = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    revoked = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    permanent = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    timeout = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
    permissions = Attribute(permission=ApikeyPermissions.VIEW_OTHERS)
