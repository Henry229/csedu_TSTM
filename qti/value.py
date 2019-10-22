from .element import Element


class Value(Element):
    qtiTagName = 'value'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.value = ''

    def get_used_attributes(self):
        return [
            'BaseType', 'FieldIdentifier'
        ]

    def __str__(self):
        return self.value

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def to_dict(self, filter_variable_content=False, filtered=None):
        return {
            'value': self.value,
            'fieldIdentifier': str(self.get_attribute('fieldIdentifier')),
            'baseType': str(self.get_attribute('baseType')),
            'cardinality': 'single'
        }
