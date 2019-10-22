from .container.containertable import ContainerTable
from .element import Element


class Table(Element):
    qtiTagName = 'table'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.body = ContainerTable()

    def get_body(self):
        return self.body

    def get_used_attributes(self):
        return ['Summary']
