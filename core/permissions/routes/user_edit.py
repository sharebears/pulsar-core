import flask

from core.permissions import Permissions
from core.utils import require_permission

from . import bp

app = flask.current_app


@bp.route('/permissions', methods=['GET'])
@require_permission('permissions_modify')
def view_permissions(user_id: int = None,
                     all: bool = False) -> flask.Response:
    """
    View all permissions available. Requires the ``permissions_modify`` permission.

    .. :quickref: Permission; View available permissions.

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": [
           "list_permissions",
           "permissions_modify",
           "users_change_password"
         ]
       }

    :>json list response: A list of permission name strings

    :statuscode 200: View successful
    :statuscode 403: User lacks sufficient permissions to view permissions
    """
    return flask.jsonify({'permissions': Permissions.get_all_permissions()})
