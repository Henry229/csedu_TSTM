from .attribute import Attribute


class Label(Attribute):
    name = 'label'
    type = 'String256'
    defaultValue = None
    required = False

