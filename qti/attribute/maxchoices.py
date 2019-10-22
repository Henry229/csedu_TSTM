from .attribute import Attribute


class MaxChoices(Attribute):
    name = 'maxChoices'
    type = 'QtiInteger'
    required = True
    defaultValue = 1
