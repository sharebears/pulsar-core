import flask
from voluptuous import Email, Optional, Schema

from pulsar import APIException, db
from pulsar.models import Invite
from pulsar.utils import choose_user, require_permission, validate_data
from pulsar.validators import bool_get

from . import bp

app = flask.current_app


VIEW_INVITE_SCHEMA = Schema({
    'id': str,
    }, required=True)


@bp.route('/invite', methods=['GET'])
@require_permission('view_invites')
@validate_data(VIEW_INVITE_SCHEMA)
def view_invite(id: str) -> flask.Response:
    """
    View the details of an invite. Requires the ``view_invites`` permission.
    Requires the ``view_invites_others`` permission to view another user's invites.

    .. :quickref: Invite; View an active invite.

    **Example request**:

    .. sourcecode:: http

       GET /invite HTTP/1.1
       Host: pul.sar
       Accept: application/json
       Content-Type: application/json

       {
         "id": "an-invite-code"
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
           "expired": false,
           "id": "an-invite-code",
           "time-sent": "1970-01-01T00:00:00.000001+00:00",
           "email": "bright@pul.sar",
           "invitee": null
         }
       }

    :>jsonarr boolean expired: Whether or not the invite is expired
    :>jsonarr string id: The invite code
    :>jsonarr string time-sent: When the invite was sent
    :>jsonarr string email: The email that the invite was sent to
    :>jsonarr dict invitee: The user invited by the invite

    :statuscode 200: View successful
    :statuscode 404: Invite does not exist or user cannot view invite
    """
    return flask.jsonify(Invite.from_id(
        id, include_dead=True, _404=True, asrt='view_invites_others'))


VIEW_INVITES_SCHEMA = Schema({
    Optional('used', default=False): bool_get,
    Optional('include_dead', default=False): bool_get,
    }, required=True)


@bp.route('/invites', methods=['GET'])
@bp.route('/invites/user/<int:user_id>', methods=['GET'])
@require_permission('view_invites')
@validate_data(VIEW_INVITES_SCHEMA)
def view_invites(used: bool,
                 include_dead: bool,
                 user_id: int = None) -> flask.Response:
    """
    View sent invites. If a user_id is specified, only invites sent by that user
    will be returned, otherwise only your invites are returned. If requester has
    the ``view_invites_others`` permission, they can view sent invites of another user.

    .. :quickref: Invite; View multiple invites.

    **Example request**:

    .. sourcecode:: http

       GET /invites HTTP/1.1
       Host: pul.sar
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": [
           {
             "expired": false,
             "id": "an-invite-code",
             "time-sent": "1970-01-01T00:00:00.000001+00:00",
             "email": "bright@pul.sar",
             "invitee": null
           },
           {
             "expired": true,
             "id": "another-invite-code",
             "time-sent": "1970-01-01T00:00:00.000002+00:00",
             "email": "bitsu@qua.sar",
             "invitee": {
               "id": 2,
               "username": "bitsu",
               "other-keys": "other-values"
             }
           }
         ]
       }

    :query boolean used: (Optional) Whether or not to only show used invites
        (overrides ``include_dead``)
    :query boolean include_dead: (Optional) Whether or not to include expired invites

    :>json list response: A list of invite data

    :>jsonarr boolean expired: Whether or not the invite is expired
    :>jsonarr string id: The invite code
    :>jsonarr string time-sent: When the invite was sent
    :>jsonarr string email: The email that the invite was sent to
    :>jsonarr dict invitee: The user invited by the invite

    :statuscode 200: View successful
    :statuscode 403: User does not have permission to view user's invites
    """
    user = choose_user(user_id, 'view_invites_others')
    invites = Invite.from_inviter(user.id, include_dead=include_dead, used=used)
    return flask.jsonify(invites)


USER_INVITE_SCHEMA = Schema({
    'email': Email(),
    }, required=True)


@bp.route('/invites', methods=['POST'])
@require_permission('send_invites')
@validate_data(USER_INVITE_SCHEMA)
def invite_user(email: str):
    """
    Sends an invite to the provided email address. Requires the ``send_invites``
    permission. If the site is open registration, this endpoint will raise a
    400 Exception.

    .. :quickref: Invite; Send an invite.

    **Example request**:

    .. sourcecode:: http

       POST /invites/an-invite-code HTTP/1.1
       Host: pul.sar
       Accept: application/json
       Content-Type: application/json

       {
         "email": "bright@puls.ar"
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
           "expired": true,
           "id": "an-invite-code",
           "time-sent": "1970-01-01T00:00:00.000001+00:00",
           "email": "bright@pul.sar",
           "invitee": null
         }
       }

    :<json string email: E-mail to send the invite to

    :>jsonarr boolean expired: Whether or not the invite is expired (always false)
    :>jsonarr string id: The invite code
    :>jsonarr string time-sent: When the invite was sent
    :>jsonarr string email: The email that the invite was sent to
    :>jsonarr dict invitee: The user invited by the invite

    :statuscode 200: Successfully sent invite
    :statuscode 400: Unable to send invites or incorrect email
    :statuscode 403: Unauthorized to send invites
    """
    if not app.config['REQUIRE_INVITE_CODE']:
        raise APIException(
            'An invite code is not required to register, so invites have been disabled.')
    if not flask.g.user.invites:
        raise APIException('You do not have an invite to send.')

    invite = Invite.new(
        inviter_id=flask.g.user.id,
        email=email,
        ip=flask.request.remote_addr)
    flask.g.user.invites -= 1
    db.session.add(invite)
    db.session.commit()
    return flask.jsonify(invite)


@bp.route('/invite', methods=['DELETE'])
@require_permission('revoke_invites')
@validate_data(VIEW_INVITE_SCHEMA)
def revoke_invite(id: str) -> flask.Response:
    """
    Revokes an active invite code, preventing it from being used. The
    invite is returned to the user's account. Requires the
    ``revoke_invites`` permission to revoke one's own sent invite, and the
    ``revoke_invites_others`` permission to revoke another user's invites.

    .. :quickref: Invite; Revoke an active invite.

    **Example request**:

    .. sourcecode:: http

       DELETE /invite HTTP/1.1
       Host: pul.sar
       Accept: application/json

       {
         "id": "an-invite-code"
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
           "expired": true,
           "id": "an-invite-code",
           "time-sent": "1970-01-01T00:00:00.000001+00:00",
           "email": "bright@pul.sar",
           "invitee": null
         }
       }

    :>jsonarr boolean expired: Whether or not the invite is expired (always true)
    :>jsonarr string id: The invite code
    :>jsonarr string time-sent: When the invite was sent
    :>jsonarr string email: The email that the invite was sent to
    :>jsonarr dict invitee: The user invited by the invite

    :statuscode 200: Revocation successful
    :statuscode 403: Unauthorized to revoke invites
    :statuscode 404: Invite does not exist or user cannot view invite
    """
    invite = Invite.from_id(id, _404=True, asrt='revoke_invites_others')
    invite.expired = True
    invite.inviter.invites += 1
    db.session.commit()
    return flask.jsonify(invite)
