from core.mixins import Permission


class PermissionPermissions(Permission):
    MODIFY = 'permissions_modify'


class UserclassPermissions(Permission):
    LIST = 'userclasses_list'
    MODIFY = 'userclasses_modify'
