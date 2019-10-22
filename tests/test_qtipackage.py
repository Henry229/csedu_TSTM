import os
import shutil
import unittest

from lxml import etree

from app import create_app, db


class QtiPackageTestCase(unittest.TestCase):
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

    def test_cse_lc_package(self):
        """
        CSE LC Qti package
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/nap_cs_y5_s01_lc_1558570535.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            self.assertNotEqual(qti_item.get_identifier(), None)
            self.assertNotEqual(qti_item.get_attribute_value('title'), None)
            self.assertNotEqual(qti_item.get_interaction_type(), None)
            self.assertNotEqual(qti_item.get_cardinality(), None)
            self.assertNotEqual(qti_item.get_base_type(), None)
            self.assertNotEqual(qti_item.get_correct_response(), None)

    def test_cse_rd_package(self):
        """
        CSE LC Qti package
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/nap_cs_y5_s01_rd_1558570586.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            self.assertNotEqual(qti_item.get_identifier(), None)
            self.assertNotEqual(qti_item.get_attribute_value('title'), None)
            self.assertNotEqual(qti_item.get_interaction_type(), None)
            self.assertNotEqual(qti_item.get_cardinality(), None)
            self.assertNotEqual(qti_item.get_base_type(), None)
            self.assertNotEqual(qti_item.get_correct_response(), None)

    def test_cse_num_package(self):
        """
        CSE LC Qti package
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/nap_cs_y5_s01_num_1558570488.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            self.assertNotEqual(qti_item.get_identifier(), None)
            self.assertNotEqual(qti_item.get_attribute_value('title'), None)
            self.assertNotEqual(qti_item.get_interaction_type(), None)
            self.assertNotEqual(qti_item.get_cardinality(), None)
            self.assertNotEqual(qti_item.get_base_type(), None)
            self.assertNotEqual(qti_item.get_correct_response(), None)

    def test_cse_lc_package_to_qti(self):
        """
        CSE LC Qti package: export to QTI xml
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/nap_cs_y5_s01_lc_1558570535.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            qti_xml = qti_item.to_qti()
            self.assertNotEqual(qti_xml, '')

    def test_associate_things_package_to_qti(self):
        """
        associate_things_1560343053 package: export to QTI xml
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/associate_things_1560343053.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            qti_xml = qti_item.to_qti()
            self.assertNotEqual(qti_xml, '')
            tree = etree.XML(str.encode(qti_xml))
            self.assertNotEqual(tree, None)
            new_qti_xml = etree.tostring(tree, pretty_print=True, encoding='unicode')
            self.assertNotEqual(new_qti_xml, None)

    def test_example_3_baudelaire_package_to_qti(self):
        """
        example_3_baudelaire_1561985756 package: export to QTI xml
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/example_3_baudelaire_1561985756.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            qti_xml = qti_item.to_qti()
            self.assertNotEqual(qti_xml, '')
            tree = etree.XML(str.encode(qti_xml))
            self.assertNotEqual(tree, None)
            new_qti_xml = etree.tostring(tree, pretty_print=True, encoding='unicode')
            self.assertNotEqual(new_qti_xml, None)

    def test_custom_response_processing_package_to_qti(self):
        """
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                'data/qti_packages/custom_response_processing.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            qti_xml = qti_item.to_qti()
            self.assertNotEqual(qti_xml, '')
            tree = etree.XML(str.encode(qti_xml))
            self.assertNotEqual(tree, None)
            new_qti_xml = etree.tostring(tree, pretty_print=True, encoding='unicode')
            self.assertNotEqual(new_qti_xml, None)

    @unittest.skip("Only for bug fix.")
    def test_bug_fix_package_to_qti(self):
        """
        example_3_baudelaire_1561985756 package: export to QTI xml
        :return:
        """
        from qti.loader.packageloader import PackageLoader

        loader = PackageLoader()
        qti_items = loader.import_qti_package_file(os.path.join(self.basedir,
                                                                '../storage/i1490833782412938251.zip'))
        self.assertFalse(qti_items is None)
        for qti_item in qti_items:
            qti_xml = qti_item.to_qti()
            self.assertNotEqual(qti_xml, '')
            tree = etree.XML(str.encode(qti_xml))
            self.assertNotEqual(tree, None)
            new_qti_xml = etree.tostring(tree, pretty_print=True, encoding='unicode')
            self.assertNotEqual(new_qti_xml, None)
