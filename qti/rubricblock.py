from .container.containerstatic import ContainerStatic
from .container.flowcontainer import FlowContainerMixin
from .contentvariable import ContentVariableMixin
from .element import Element


class RubricBlock(FlowContainerMixin, ContentVariableMixin, Element):
    qtiTagName = 'rubricBlock'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.body = ContainerStatic()

    def get_body(self):
        return self.body

    def get_used_attributes(self):
        return [
            'View', 'UseAttribute'
        ]

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        if filter_variable_content:
            filtered[self.get_serial()] = data
            data = {
                'serial': data.get('serial'),
                'qtiClass': data.get('qtiClass')
            }
        return data

    def to_filtered_dict(self):
        return self.to_dict(filter_variable_content=True)
