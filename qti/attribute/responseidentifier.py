from .attribute import Attribute


class ResponseIdentifier(Attribute):
    name = 'responseIdentifier'
    type = 'IdentifierResponse'
    required = True
    defaultValue = None
