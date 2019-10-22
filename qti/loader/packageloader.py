import os
import re
from zipfile import ZipFile, BadZipFile

from lxml import etree

from qti.itemservice.importservice import ImportService
from ..exceptions import QtiLoaderError
from ..loader.itemloader import ItemLoader
from ..resource import Resource


class PackageLoader:
    def __init__(self):
        self.manifestNamespace = ''
        self.package_zip = None
        self.itemStorage = os.path.abspath(os.path.dirname(__file__)) + "/../../storage/"

    def import_qti_package_file(self, file):
        parsed_items = []
        try:
            self.package_zip = ZipFile(file)
        except BadZipFile:
            return parsed_items

        # parse manifest file
        with self.package_zip.open('imsmanifest.xml', 'r') as manifest_file:
            item_resources = self.parse_manifest_xml(manifest_file)

        # resource 별로 하나의 item 이 존재한다.
        for resource in item_resources:
            import_service = ImportService(resource.get_identifier(), resource)
            # item parsing 한다. 그리고 xml 로 저장한다.
            item_file_name = resource.get_file()
            with self.package_zip.open(item_file_name, 'r') as item_file:
                loader = ItemLoader(item_file)
                try:
                    item = loader.build_item()
                    item.set_resource_id(resource.get_identifier())
                    parsed_items.append(item)
                    # file 로 저장한다.
                    q = item.to_qti()
                    import_service.save_qti(q)
                except QtiLoaderError as e:
                    print('QtiLoaderError: ' + str(e))
                    continue
            # image, css 와 같은 파일을 저장한다.
            import_service.save_auxiliary_files(self.package_zip)
        self.package_zip.close()

        return parsed_items

    def parse_manifest_xml(self, manifest_file):
        manifest_xml = etree.parse(manifest_file)
        manifest = manifest_xml.getroot()
        if simple_name(manifest.tag) != 'manifest':
            raise ValueError()
        self.manifestNamespace = manifest.nsmap.get(None, '')

        resources = []
        resource_nodes = manifest.xpath("//*[name(.)='resource']")
        for node in resource_nodes:
            resource_type = node.get('type')
            if not Resource.is_assessment_item(resource_type):
                continue
            identifier = node.get('identifier')
            href = node.get('href', '')
            aux_files = []
            file_nodes = self.findall('file', node)
            for file_node in file_nodes:
                file_href = file_node.get('href', '')
                if href != file_href:
                    aux_files.append(file_href)

            dependency_nodes = self.findall('dependency', node)
            for dependency_node in dependency_nodes:
                ref = dependency_node.get('identifierref')
                ref_resource_nodes = manifest.xpath("//*[name(.)='resource' and @identifier='" + ref + "']")
                for ref_node in ref_resource_nodes:
                    if ref_node.get('href') is not None:
                        aux_files.append(ref_node.get('href'))

            resource = Resource(identifier, resource_type, href)
            resource.set_auxiliary_files(aux_files)
            resources.append(resource)

        return resources

    def get_resource_base_dir(self, resource):
        return self.itemStorage + resource.get_identifier() + '/'

    def get_resource_qti_files_dir(self, resource):
        return self.get_resource_base_dir(resource) + 'itemContent/en-US/'

    def create_resource_base_dirs(self, resource):
        os.makedirs(self.get_resource_base_dir(resource) + 'itemContent/en-US', exist_ok=True)

    def findall(self, tag_name, context_node):
        return context_node.findall('{' + self.manifestNamespace + '}' + tag_name)


def simple_name(long_name):
    return re.sub(r'{.+?}', '', long_name)
