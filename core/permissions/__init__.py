from core.permissions.routes import bp  # noqa

PERMISSIONS = [
    'modify_permissions',  # View all permissions and modify permissions of users
    'list_user_classes',  # View all user classes
    'modify_user_classes',  # Modify permissions of and create user classes
]

BASIC_PERMISSIONS = [
    'create_forum_posts',
    'create_forum_threads',
    'send_invites',
]
