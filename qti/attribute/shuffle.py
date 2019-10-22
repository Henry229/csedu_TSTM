from .attribute import Attribute


class Shuffle(Attribute):
    name = 'shuffle'
    type = 'QtiBoolean'
    required = False
    defaultValue = 'false'
