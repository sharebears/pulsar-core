import flask
from . import bp
from .models import User
from pulsar import _404Exception
from pulsar.utils import require_permission

app = flask.current_app


@bp.route('/users/<int:user_id>', methods=['GET'])
@require_permission('view_users')
def get_user(user_id):
    """
    Return general information about a user with the given user ID.  If the
    user is getting information about themselves, the API will return more
    detailed data about the user. If the requester has the
    ``moderate_users`` permission, the API will return _even more_ data.

    .. :quickref: User; Get user information.

    **Example request**:

    .. sourcecode:: http

       GET /users/1 HTTP/1.1
       Host: pul.sar
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
           "id": 1,
           "username": "lights",
           "invites": 2
         }
       }

    :>jsonarr int id: User ID of user
    :>jsonarr string username: Username of user
    :>jsonarr int invites: (Restricted to self view) Invites available to user

    :statuscode 200: User exists
    :statuscode 404: User does not exist
    """
    user = User.from_id(user_id)
    if not user:
        raise _404Exception('User')

    if flask.g.user.has_permission('moderate_users'):
        return flask.jsonify(user.to_dict(very_detailed=True))
    elif flask.g.user == user:
        return flask.jsonify(user.to_dict(detailed=True))
    else:
        return flask.jsonify(user.to_dict())