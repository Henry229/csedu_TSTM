from .identifiedelement import IdentifiedElement
from .utils import ClassUtils


class IdentifierCollection:
    def __init__(self, identified_elements=None):
        self.elements = {}
        if identified_elements is None:
            identified_elements = {}
        self.add_multiple(identified_elements)

    def add(self, element: IdentifiedElement):
        identifier = element.get_identifier(False)
        if identifier is not None:
            if self.elements.get(identifier) is None:
                self.elements[identifier] = {}

            self.elements[identifier][element.get_serial()] = element

    def exists(self, identifier):
        return self.elements.get(identifier) is not None

    def get(self, identifier=''):
        result = {}
        if identifier == '':
            result = self.elements
        elif self.exists(identifier):
            result = self.elements.get(identifier)
        return result

    def get_unique(self, identifier, element_class=''):
        unique = None
        if self.exists(identifier):
            if element_class == '':
                if len(self.elements[identifier]) > 1:
                    raise ValueError("Multiple identifier.")
                elif len(self.elements[identifier]) == 1:
                    for val in self.elements[identifier].values():
                        unique = val
                        break
            else:
                found = []
                for ele in self.elements[identifier].values():
                    if ClassUtils.is_subclass_by_name(ele, element_class):
                        found.append(ele)
                if len(found) > 1:
                    raise ValueError("Multiple identifier.")
                elif len(found) == 1:
                    unique = found[0]
        return unique

    def add_multiple(self, identified_elements):
        for element in identified_elements.values():
            if isinstance(element, IdentifiedElement):
                self.add(element)
            elif type(element) is list:
                self.add_multiple(element)

    def merge(self, identified_collection):
        for elements in identified_collection.get():
            self.add_multiple(elements)
