import json

import flask

from . import bp


@bp.after_app_request
def hook(response: flask.Response) -> flask.Response:
    wrap_response(response)
    return response


def wrap_response(response: flask.Response) -> None:
    """
    Wrap response with the homogenized response dictionary, containing
    a ``status`` key.

    :param response: The flask response en route to user
    """
    try:
        data = json.loads(response.get_data())
    except ValueError:  # pragma: no cover
        data = 'Could not encode response.'

    response_data = {
        'status': 'success' if response.status_code // 100 == 2 else 'failed',
        'response': data,
        }

    if flask.g.user and flask.g.user.has_permission('view_cache_keys'):
        # We can't encode sets to JSON.
        response_data['cache_keys'] = {k: list(v) for k, v in flask.g.cache_keys.items()}

    response.set_data(json.dumps(response_data))
