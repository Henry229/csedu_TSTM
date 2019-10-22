
from .element import Element


class IdentifiedElement(Element):
    def __init__(self, attributes=None, related_item=None, serial=''):
        if attributes is None:
            attributes = {}
        self.identifier = ''
        super().__init__(attributes, related_item, serial)

    def get_used_attributes(self):
        raise NotImplementedError()

    def set_attribute(self, name, value):
        if name == 'identifier':
            self.set_identifier(value)
        else:
            super().set_attribute(name, value)

    def to_dict(self, filter_variable_content=False, filtered=None):
        if filtered is None:
            filtered = []
        data = super().to_dict(filter_variable_content, filtered)
        data['identifier'] = self.get_identifier()
        return data

    def set_identifier(self, identifier, collision_free=False):
        result = False
        if identifier == '' or identifier is None:
            raise ValueError()

        if self.is_identifier_available(identifier):
            result = True
        else:
            if collision_free:
                identifier = self.generate_identifier(identifier)
                result = True
            else:
                raise ValueError("The identifier " + identifier + " is already in use")

        self.identifier = identifier

        return result

    def get_identifier(self, generate=True):
        if self.identifier == '' and generate:
            related_item = self.get_related_item()
            if related_item is not None:
                self.identifier = self.generate_identifier()

        return self.identifier

    def get_attribute_value(self, name):
        if name == 'identifier':
            return self.get_identifier()
        else:
            return super().get_attribute_value(name)

    def get_attribute_values(self, filter_none=True):
        values = super().get_attribute_values(filter_none)
        values['identifier'] = self.get_identifier()
        return values

    def generate_identifier(self, prefix=''):
        related_item = self.relatedItem
        if related_item is None:
            raise ValueError()
        return 'ToDo_not_implemented'

    def validate_current_identifier(self, collision_free=False):
        valid = False
        if self.identifier == '':
            valid = True
        else:
            valid = self.set_identifier(self.identifier, collision_free)
        return valid

    def is_identifier_available(self, identifier):
        available = False
        if self.identifier != '' and self.identifier == identifier:
            available = True
        else:
            related_item = self.get_related_item()
            if related_item is None:
                available = True
            else:
                id_collection = related_item.get_identified_elements()
                available = not id_collection.exists(identifier)

        return available
