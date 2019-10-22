from .attribute import Attribute


class MinChoices(Attribute):
    name = 'minChoices'
    type = 'QtiInteger'
    required = True
    defaultValue = 0
