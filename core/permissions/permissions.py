from core.permissions import PermissionsEnum


class PermissionPermissions(PermissionsEnum):
    MODIFY = 'permissions_modify'


class UserclassPermissions(PermissionsEnum):
    LIST = 'userclasses_list'
    MODIFY = 'userclasses_modify'
