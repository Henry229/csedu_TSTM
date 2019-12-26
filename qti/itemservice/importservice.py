import os
import shutil

from qti.resource import Resource
from .itemservice import ItemService


class ImportService(ItemService):

    def __init__(self, item_identifier, resource: Resource):
        super().__init__(item_identifier)
        self.resource = resource
        os.makedirs(self.get_qti_files_dir(), exist_ok=True)

    def save_qti(self, qti_xml):
        file_path = self.get_qti_xml_path()
        with open(file_path, 'w', encoding='utf8') as f:
            f.write(qti_xml)

    def save_auxiliary_files(self, package_zip):
        """
        예)
        * zip 파일 폴더 구조
            i1561776787155446
            ├── 1024px-Gustave_Courbet_033.jpg
            ├── qti.xml
            └── style
                └── custom
                    └── tao-user-styles.css
        * storage 폴더 구조
            i1561776787155446
            └── itemContent
                └── en-US
                    ├── 1024px-Gustave_Courbet_033.jpg
                    ├── qti.xml
                    └── style
                        └── custom
                            └── tao-user-styles.css
        :param package_zip:
        :return:
        """
        # package 에 있는 qti.xml 파일이 위치한 폴더를 base_dir 로 한다.
        item_file_name = self.resource.get_file()
        base_dir = item_file_name.rsplit('/', 1)[0] if len(item_file_name.rsplit('/')) > 1 else ''
        for auxiliary_file in self.resource.get_auxiliary_files():
            package_zip.extract(auxiliary_file, self.get_qti_base_temp_dir())
            # qti.xml 이 위치한 폴더를 기준으로 위치할 path를 구한다.
            dest_file = auxiliary_file.replace(base_dir + '/', '') if base_dir != '' else auxiliary_file

            # 파일이 위치할 곳에 디렉토리를 생성해야한다면 생성해 준다.
            dest_dirs = dest_file.rsplit('/', 1)
            if len(dest_dirs) == 2:
                os.makedirs(os.path.join(self.get_qti_files_dir(), dest_dirs[0]), exist_ok=True)

            # rename 으로 파일을 목적지로 이동한다.
            # TODO - 중복 import가 가능하도록 처리 - 폴더, 파일 이름에 대한 규칙 정리 필요
            if not os.path.exists(os.path.join(self.get_qti_files_dir(), dest_file)):
                os.rename(os.path.join(self.get_qti_base_temp_dir(), auxiliary_file),
                          os.path.join(self.get_qti_files_dir(), dest_file))
        # 임시 폴더를 지운다.
        if os.path.exists(self.get_qti_base_temp_dir()):
            shutil.rmtree(self.get_qti_base_temp_dir())

