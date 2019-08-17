from conftest import check_json_response


def test_404_exception(app, authed_client):
    """Nonexistent route should return 404 API response."""
    response = authed_client.get('/nonexistent/endpoint')
    assert response.status_code == 404
    check_json_response(response, 'Resource does not exist.')


def test_500_exception(app, client):
    """Server error should return response in JSON."""
    app.debug = False

    @app.route('/exception_causer')
    def exception_causer():
        raise ValueError('Because I can!')

    response = client.get('/exception_causer')
    check_json_response(response, 'Something went wrong with your request.')


def test_405_exception(app, client):
    """405 exception should return response in JSON."""

    @app.route('/exception_causer', methods=['POST'])
    def exception_causer():
        return 'never hit this'

    response = client.get('/exception_causer')
    check_json_response(response, 'Method not allowed for this resource.')
