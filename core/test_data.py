from core.mixins import TestDataPopulator
from core import db
from werkzeug.security import generate_password_hash
from core.permissions.models import UserClass, SecondaryClass, secondary_class_assoc_table

HASH_1 = generate_password_hash('12345')
HASH_2 = generate_password_hash('abcdefg')
HASH_3 = generate_password_hash('password')

CODE_1 = '1234567890abcdefghij1234'
CODE_2 = 'abcdefghijklmnopqrstuvwx'
CODE_3 = '234567890abcdefghij12345'
CODE_4 = 'zbjfeaofe38232r2qpfewfoo'

HASHED_CODE_1 = generate_password_hash(CODE_1)
HASHED_CODE_2 = generate_password_hash(CODE_2)
HASHED_CODE_3 = generate_password_hash(CODE_3)
HASHED_CODE_4 = generate_password_hash(CODE_4)


class CorePopulator(TestDataPopulator):

    @classmethod
    def populate(cls):
        UserClass.new(name='User')
        SecondaryClass.new(name='FLS')
        UserClass.new(name='user_v2', permissions=[
            'permissions_modify',
            'users_edit_settings',
            ])
        SecondaryClass.new(name='user_v2', permissions=[
            'users_edit_settings',
            ])

        db.engine.execute(  # Generating password hash each time is slow, so raw SQL we go.
            f"""INSERT INTO users
            (username, passhash, email, invites, inviter_id, user_class_id) VALUES
            ('user_one', '{HASH_1}', 'user_one@puls.ar', 1, NULL, 1),
            ('user_two', '{HASH_2}', 'user_two@puls.ar', 0, 1, 1),
            ('user_three', '{HASH_3}', 'user_three@puls.ar', 0, NULL, 1)
            """)
        db.engine.execute(
            f"""INSERT INTO api_keys (user_id, hash, keyhashsalt, revoked, permissions) VALUES
            (1, 'abcdefghij', '{HASHED_CODE_1}', 'f',
             '{{"sample_permission", "sample_2_permission", "sample_3_permission"}}'),
            (1, 'cdefghijkl', '{HASHED_CODE_3}', 'f', '{{}}'),
            (2, 'bcdefghijk', '{HASHED_CODE_3}', 'f', '{{}}'),
            (2, '1234567890', '{HASHED_CODE_2}', 't', '{{}}')""")
        db.engine.execute(
            f"""INSERT INTO invites (inviter_id, invitee_id, email, code, expired) VALUES
            (1, NULL, 'bright@puls.ar', '{CODE_1}', 'f'),
            (1, 2, 'bright@quas.ar', '{CODE_2}', 't'),
            (2, NULL, 'bright@puls.ar', '{CODE_3}', 'f'),
            (1, NULL, 'bright@quas.ar', '{CODE_4}', 't')
            """)

        db.session.execute(
            secondary_class_assoc_table.insert().values(user_id=1, secondary_class_id=1))
        db.session.commit()

    @classmethod
    def unpopulate(cls):
        db.engine.execute("DELETE FROM notifications")
        db.engine.execute("DELETE FROM notifications_types")
        db.engine.execute("DELETE FROM secondary_class_assoc")
        db.engine.execute("DELETE FROM users_permissions")
        db.engine.execute("DELETE FROM api_keys")
        db.engine.execute("DELETE FROM invites")
        db.engine.execute("DELETE FROM users")
        db.engine.execute("DELETE FROM user_classes")
        db.engine.execute("DELETE FROM secondary_classes")
        db.engine.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
        db.engine.execute("ALTER SEQUENCE user_classes_id_seq RESTART WITH 1")
        db.engine.execute("ALTER SEQUENCE secondary_classes_id_seq RESTART WITH 1")
