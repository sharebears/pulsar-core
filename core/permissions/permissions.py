from core.mixins import Permission


class PermissionPermissions(Permission):
    MODIFY = 'permissions_modify'


class UserclassPermissions(Permission):
    LIST = 'user_classes_list'
    MODIFY = 'user_classes_modify'
