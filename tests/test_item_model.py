import unittest

from app import create_app, db
from app.models import Role


class ItemModelTestCase(unittest.TestCase):
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

    # def test_password_setter(self):
    #     u = User(password='cat')
    #     self.assertTrue(u.password_hash is not None)
    #
    # def test_no_password_getter(self):
    #     u = User(password='cat')
    #     with self.assertRaises(AttributeError):
    #         u.password

    # def test_get_codes(self):
    #     self.assertTrue(Codebook.get_code_id('subject') is not None)
