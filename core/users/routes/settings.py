import flask
from voluptuous import All, Length, Match, Schema

from core import _401Exception, _403Exception, db
from core.users.models import APIKey, User
from core.users.permissions import UserPermissions
from core.utils import access_other_user, require_permission, validate_data
from core.validators import PASSWORD_REGEX

from . import bp

app = flask.current_app

SETTINGS_SCHEMA = Schema({
    # Length restrictions inaccurate for legacy databases and testing.
    'existing_password': All(str, Length(min=5, max=512)),
    'new_password': Match(PASSWORD_REGEX, msg=(
        'Password must be between 12 and 512 characters and contain at least 1 letter, '
        '1 number, and 1 special character')),
    })


@bp.route('/users/settings', methods=['PUT'])
@require_permission(UserPermissions.EDIT_SETTINGS)
@validate_data(SETTINGS_SCHEMA)
@access_other_user(UserPermissions.MODERATE)
def users_edit_settings(user: User,
                        existing_password: str =None,
                        new_password: str =None) -> flask.Response:
    """
    Change a user's settings. Requires the ``users_edit_settings`` permission.
    Requires the ``users_moderate`` permission to change another user's
    settings, which can be done by specifying a ``user_id``.

    .. :quickref: Settings; Change settings.

    **Example request**:

    .. parsed-literal::

       PUT /users/settings HTTP/1.1

       {
         "existing_password": "y-&~_Wbt7wjkUJdY<j-K",
         "new_password": "an-ev3n-be77er-pa$$w0rd"
       }

    **Example response**:

    .. parsed-literal::

       {
         "status": "success",
         "response": "Settings updated."
       }

    :json string existing_password: User's existing password, not needed
        if setting another user's password with ``moderate_user`` permission.
    :json string new_password: User's new password. Must be 12+ characters and contain
        at least one letter, one number, and one special character.

    :statuscode 200: Settings successfully updated
    :statuscode 400: Settings unsuccessfully updated
    :statuscode 403: User does not have permission to change user's settings
    """
    if new_password:
        if not flask.g.user.has_permission(UserPermissions.CHANGE_PASS):
            raise _403Exception(
                message='You do not have permission to change this password.')
        if not existing_password or not user.check_password(existing_password):
            raise _401Exception(message='Invalid existing password.')
        user.set_password(new_password)
        APIKey.update_many(
            pks=APIKey.hashes_from_user(user.id),
            update={'revoked': True})

    db.session.commit()
    return flask.jsonify('Settings updated.')
