import os
import shutil
import unittest

from app import create_app, db


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.basedir = os.path.abspath(os.path.dirname(__file__))
        # Remove all files in storage directory
        for file in os.scandir(self.app.config['STORAGE_DIR']):
            shutil.rmtree(file.path)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
