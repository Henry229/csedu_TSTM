from .attribute import Attribute


class Title(Attribute):
    name = 'title'
    type = 'QtiString'
    defaultValue = None
    required = True

