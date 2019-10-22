
from .identifiedelement import IdentifiedElement


class VariableDeclaration(IdentifiedElement):
    """
    Item variables are declared by variable declarations. All variables must be declared except for the built-in
    session variables referred to below which are declared implicitly and must not be declared.
    The purpose of the declaration is to associate an identifier with the variable and to identify the runtime
    type of the variable's value.

        - reference: https://www.imsglobal.org/question/qtiv2p1/imsqti_infov2p1.html#element10037
    """
    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.defaultValue = None

    def get_used_attributes(self):
        return []

    def get_default_value(self):
        return self.defaultValue

    def set_default_value(self, value):
        self.defaultValue = value

    def get_composing_elements(self, class_name=''):
        return []
