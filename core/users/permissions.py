from core.permissions import PermissionsEnum


class UserPermissions(PermissionsEnum):
    VIEW = 'users_view'
    CHANGE_PASS = 'users_change_password'
    EDIT_SETTINGS = 'users_edit_settings'
    MODERATE = 'users_moderate'
    MODERATE_ADVANCED = 'users_moderate_advanced'


class InvitePermissions(PermissionsEnum):
    SEND = 'invites_send'
    VIEW = 'invites_view'
    VIEW_OTHERS = 'invites_view_others'
    REVOKE = 'invites_revoke'
    REVOKE_OTHERS = 'invites_revoke_others'


class ApikeyPermissions(PermissionsEnum):
    VIEW = 'api_keys_view'
    VIEW_OTHERS = 'api_keys_view_others'
    REVOKE = 'api_keys_revoke'
    REVOKE_OTHERS = 'api_keys_revoke_others'


class SitePermissions(PermissionsEnum):
    NO_IP_HISTORY = 'site_no_ip_history'
    MANAGE_CACHE_KEYS = 'site_manage_cache_keys'
    NO_POST_LENGTH_LIMIT = 'site_no_post_length_limit'
    GOD_MODE = 'site_god_mode'
