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
    db.engine.execute("""INSERT INTO user_classes (name, permissions) VALUES
                      ('user_v2', '{"permissions_modify", "users_edit_settings"}')""")
    db.engine.execute("""INSERT INTO secondary_classes (name, permissions) VALUES
                      ('user_v2', '{"users_edit_settings"}')""")
