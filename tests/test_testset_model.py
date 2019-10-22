import unittest

from app import create_app, db
from app.models import Testset


class TestsetModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_parsingStageData(self):
        testset = Testset.query.filter_by(active=True).first_or_404()
        data = testset.parsingStageData()
        self.assertTrue(data is not None)
