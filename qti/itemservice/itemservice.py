import os

from ..loader.itemloader import ItemLoader


class ItemService:
    storageDir = None
    contentDir = 'itemContent/en-US'
    qtiFile = 'qti.xml'

    def __init__(self, resource_id):
        """
        self.resource_id : item 이 저장되는 폴더명.
        :param resource_id:
        """
        self.resource_id = resource_id

    @staticmethod
    def initialize(storage_dir):
        """
        앱 생성시 호출한다.
        :param storage_dir:
        :return:
        """
        ItemService.storageDir = storage_dir

    def get_storage_dir(self):
        return self.storageDir

    def get_qti_files_dir(self):
        return os.path.join(self.get_qti_base_dir(), self.contentDir)

    def get_qti_base_dir(self):
        return os.path.join(self.storageDir, self.resource_id)

    def get_qti_xml_path(self):
        return os.path.join(self.get_qti_files_dir(), self.qtiFile)

    def get_qti_base_temp_dir(self):
        return os.path.join(self.get_qti_base_dir(), 'temp')

    def get_item(self):
        qti_xml = self.get_qti_xml_path()
        loader = ItemLoader(qti_xml)
        item = loader.build_item()
        item.set_resource_id(self.resource_id)
        return item


