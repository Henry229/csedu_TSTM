import os
import shutil
import unittest

from app import create_app, db


class ItemPreviewTestCase(unittest.TestCase):
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

    def test_single_choice(self):
        """
        Import a qti item package and build preview XHTML.
        :return:
        """
        from qti.loader.packageloader import PackageLoader
        from qti.itemservice.itemservice import ItemService

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/signle_choice_01.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            item_service = ItemService(qti_item.get_resource_id())
            item = item_service.get_item()
            self.assertNotEqual(item, None)
            rendered = item.to_html()
            self.assertNotEqual(rendered, None)
            break

    def test_single_choice_with_img(self):
        """
        Import a qti item package and build preview XHTML.
        :return:
        """
        from qti.loader.packageloader import PackageLoader
        from qti.itemservice.itemservice import ItemService

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/single_choice_with_img.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            item_service = ItemService(qti_item.get_resource_id())
            item = item_service.get_item()
            self.assertNotEqual(item, None)
            rendered = item.to_html()
            self.assertNotEqual(rendered, None)
            break
