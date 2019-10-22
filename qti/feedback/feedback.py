from ..container.containerstatic import ContainerStatic
from ..container.flowcontainer import FlowContainerMixin
from ..contentvariable import ContentVariableMixin
from ..identifiedelement import IdentifiedElement


class Feedback(ContentVariableMixin, FlowContainerMixin, IdentifiedElement):
    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.body = ContainerStatic('', related_item)

    def get_body(self):
        return self.body

    def get_used_attributes(self):
        return [
            'OutcomeIdentifier', 'ShowHideTemplateElement'
        ]

    def is_identifier_available(self, identifier):
        if identifier == '' or identifier in None:
            raise ValueError()
        result = False
        if self.identifier is not None and self.identifier == identifier:
            result = True
        else:
            related_item = self.get_related_item()
            if related_item is not None:
                result = True
            else:
                collection = related_item.get_i

