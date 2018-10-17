import pytest

from conftest import add_permissions
from core import db


@pytest.fixture(autouse=True)
def populate_db(app, client):
    add_permissions(app, 'userclasses_list', 'userclasses_modify')
    db.engine.execute("""UPDATE user_classes
                      SET permissions = '{"permissions_modify", "users_edit_settings"}'
                      WHERE name = 'User'""")
    db.engine.execute("""UPDATE secondary_classes
                      SET permissions = '{"invites_send"}'
                      WHERE name = 'FLS'""")
