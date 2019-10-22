class Resource:
    allowedTypes = [
        'imsqti_apipsectionroot_xmlv2p1',
        'controlfile/apip_xmlv1p0',
        'associatedcontent/apip_xmlv1p0/learning-application-resource'
    ]

    testTypes =[
        'imsqti_apiptestroot_xmlv2p1',
        'imsqti_test_xmlv2p1',
        'imsqti_test_xmlv2p2',
        'imsqti_assessment_xmlv2p1'
    ]

    itemTypes = [
        'imsqti_item_xmlv2p0',
        'imsqti_item_xmlv2p1',
        'imsqti_item_xmlv2p2',
        'imsqti_apipitemroot_xmlv2p1',
        'imsqti_apipitem_xmlv2p1'
    ]

    def __init__(self, identifier, resource_type, file):
        self.identifier = identifier
        self.type = resource_type
        self.file = file
        self.auxiliaryFiles = []
        self.dependencies = []

    @staticmethod
    def is_allowed(resource_type):
        if resource_type and resource_type in Resource.allowedTypes:
            return True

        if Resource.is_assessment_item(resource_type) or Resource.is_assessment_test(resource_type):
            return True

        return False

    @staticmethod
    def is_assessment_item(resource_type):
        return resource_type and resource_type in Resource.itemTypes

    @staticmethod
    def is_assessment_test(resource_type):
        return resource_type and resource_type in Resource.testTypes

    @staticmethod
    def get_tet_types():
        return Resource.testTypes

    @staticmethod
    def get_item_types():
        return Resource.itemTypes

    def get_identifier(self):
        return self.identifier

    def set_identifier(self, identifier):
        self.identifier = identifier

    def get_file(self):
        return self.file

    def get_type(self):
        return self.type

    def set_auxiliary_files(self, files):
        self.auxiliaryFiles = files

    def add_auxiliary_file(self, file):
        self.auxiliaryFiles.append(file)

    def get_auxiliary_files(self):
        return self.auxiliaryFiles

    def set_dependencies(self, dependencies):
        self.dependencies = dependencies

    def add_dependency(self, dependency):
        self.dependencies.append(dependency)

    def get_dependencies(self):
        return self.dependencies



