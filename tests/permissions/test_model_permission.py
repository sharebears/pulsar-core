from conftest import add_permissions
from core import db
from core.permissions.models import UserPermission
from core.users.models import User


def test_permissions_from_user(app, client):
    add_permissions(app, 'perm_one', 'perm_two')
    db.engine.execute("""INSERT INTO users_permissions (user_id, permission, granted)
                      VALUES (1, 'perm_three', 'f')""")
    perms = UserPermission.from_user(1)
    assert perms == {
        'perm_one': True,
        'perm_two': True,
        'perm_three': False,
        'list_user_classes': True,
        'modify_user_classes': True,
    }


def test_permissions_from_prefix(app, client):
    add_permissions(app, 'perm_one', 'perm_two', 'non_prefixed')
    db.engine.execute("""INSERT INTO users_permissions (user_id, permission, granted)
                      VALUES (2, 'perm_three', 't')""")
    perms = UserPermission.from_prefix(1, 'perm')
    assert len(perms) == 2
    assert set(perms) == {'perm_one', 'perm_two'}


def test_user_class_permission_override(app, authed_client):
    db.engine.execute("""UPDATE user_classes SET permissions = '{"sample_a", "sample_b"}'""")
    db.engine.execute("""UPDATE secondary_classes SET permissions = '{"sample_e"}'""")
    db.engine.execute(
        """INSERT INTO users_permissions (user_id, permission, granted) VALUES
        (1, 'sample_c', 't'),
        (1, 'sample_d', 't'),
        (1, 'sample_b', 'f')
        """)

    user = User.from_pk(1)
    assert set(user.permissions) == {
        'sample_a',
        'sample_c',
        'sample_d',
        'sample_e',
        'modify_user_classes',
        'list_user_classes'
        }
