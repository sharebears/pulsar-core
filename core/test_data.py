from core.mixins import TestDataPopulator
from core import db
from werkzeug.security import generate_password_hash

HASH_1 = generate_password_hash('12345')
HASH_2 = generate_password_hash('abcdefg')
HASH_3 = generate_password_hash('password')


class CorePopulator(TestDataPopulator):

    def populate():
        db.engine.execute("""INSERT INTO user_classes (name) VALUES ('User')""")
        db.engine.execute("""INSERT INTO secondary_classes (name) VALUES ('FLS')""")
        db.engine.execute(
            f"""INSERT INTO users
            (username, passhash, email, invites, inviter_id, user_class_id) VALUES
            ('user_one', '{HASH_1}', 'user_one@puls.ar', 1, NULL, 1),
            ('user_two', '{HASH_2}', 'user_two@puls.ar', 0, 1, 1),
            ('user_three', '{HASH_3}', 'user_three@puls.ar', 0, NULL, 1)
            """)
        db.engine.execute("""INSERT INTO secondary_class_assoc VALUES (1, 1)""")

    def unpopulate():
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
