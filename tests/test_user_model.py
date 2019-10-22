import unittest

from app import create_app, db
from app.models import User, Permission, Role, AnonymousUser


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_setter(self):
        u = User(password='cat')
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self):
        u = User(password='cat')
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(password='cat')
        self.assertTrue(u.verify_password(('cat')))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self):
        u = User(password='cat')
        u2 = User(password='cat')
        self.assertTrue(u.password_hash != u2.password_hash)

    def test_roles_and_permissions(self):
        Role.insert_roles()
        u = User(email='ashley@example.com', password='cat')
        self.assertTrue(u.can(Permission.ITEM_EXEC))
        self.assertFalse(u.can(Permission.TESTSET_MANAGE))

    def test_taker_role(self):
        r = Role.query.filter_by(name='Test_taker').first()
        u = User(email='jenny@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.ITEM_EXEC))
        self.assertFalse(u.can(Permission.ITEM_MANAGE))
        self.assertFalse(u.can(Permission.ASSESSMENT_READ))
        self.assertFalse(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertFalse(u.can(Permission.TESTLET_MANAGE))
        self.assertFalse(u.can(Permission.TESTSET_READ))
        self.assertFalse(u.can(Permission.TESTSET_MANAGE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_item_generator_role(self):
        r = Role.query.filter_by(name='Item_generator').first()
        u = User(email='jenny@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.ITEM_EXEC))
        self.assertTrue(u.can(Permission.ITEM_MANAGE))
        self.assertFalse(u.can(Permission.ASSESSMENT_READ))
        self.assertFalse(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertFalse(u.can(Permission.TESTLET_MANAGE))
        self.assertFalse(u.can(Permission.TESTSET_READ))
        self.assertFalse(u.can(Permission.TESTSET_MANAGE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_assessment_creator_role(self):
        r = Role.query.filter_by(name='Assessment_creator').first()
        u = User(email='jenny@example.com', password='cat', role=r)
        self.assertFalse(u.can(Permission.ITEM_EXEC))
        self.assertFalse(u.can(Permission.ITEM_MANAGE))
        self.assertFalse(u.can(Permission.ASSESSMENT_READ))
        self.assertTrue(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertFalse(u.can(Permission.TESTLET_MANAGE))
        self.assertFalse(u.can(Permission.TESTSET_READ))
        self.assertFalse(u.can(Permission.TESTSET_MANAGE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_itembank_manager_role(self):
        r = Role.query.filter_by(name='Itembank_manager').first()
        u = User(email='jenny@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.ITEM_EXEC))
        self.assertTrue(u.can(Permission.ITEM_MANAGE))
        self.assertFalse(u.can(Permission.ASSESSMENT_READ))
        self.assertFalse(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertTrue(u.can(Permission.TESTLET_MANAGE))
        self.assertFalse(u.can(Permission.TESTSET_READ))
        self.assertTrue(u.can(Permission.TESTSET_MANAGE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_moderator_role(self):
        r = Role.query.filter_by(name='Moderator').first()
        u = User(email='jenny@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.ITEM_EXEC))
        self.assertTrue(u.can(Permission.ITEM_MANAGE))
        self.assertFalse(u.can(Permission.ASSESSMENT_READ))
        self.assertTrue(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertFalse(u.can(Permission.TESTLET_MANAGE))
        self.assertFalse(u.can(Permission.TESTSET_READ))
        self.assertTrue(u.can(Permission.TESTSET_MANAGE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_administrator_role(self):
        r = Role.query.filter_by(name='Administrator').first()
        u = User(email='jenny@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.ITEM_EXEC))
        self.assertTrue(u.can(Permission.ITEM_MANAGE))
        self.assertTrue(u.can(Permission.ASSESSMENT_READ))
        self.assertTrue(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertTrue(u.can(Permission.TESTLET_MANAGE))
        self.assertTrue(u.can(Permission.TESTSET_READ))
        self.assertTrue(u.can(Permission.TESTSET_MANAGE))
        self.assertTrue(u.can(Permission.ADMIN))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.ITEM_EXEC))
        self.assertFalse(u.can(Permission.ITEM_MANAGE))
        self.assertFalse(u.can(Permission.ASSESSMENT_READ))
        self.assertFalse(u.can(Permission.ASSESSMENT_MANAGE))
        self.assertFalse(u.can(Permission.TESTLET_MANAGE))
        self.assertFalse(u.can(Permission.TESTSET_READ))
        self.assertFalse(u.can(Permission.TESTSET_MANAGE))
        self.assertFalse(u.can(Permission.ADMIN))

# >>> u = User()
# >>> u.password='cat'
# >>> u.password_hash
# 'pbkdf2:sha256:150000$82pWexBU$9ff1e8ab7e1949101004c224f699b1c94632c8c851a6b844b37e91d909df8bc3'
# >>> u.verify_password('cat')
# True
# >>> u.verify_password('dog')
# False
# >>> u2 = User()
# >>> u2.password = 'cat'
# >>> u2.password_hash
# 'pbkdf2:sha256:150000$YVzbuKnI$11f0caf1f9cae03091395d10f9d56107d21d7b52093e4a4f4b10e5b4022087c1'
