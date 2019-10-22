from .generic import Generic
from .identifierresponse import IdentifierResponse
from .language import Language
from .length import Length
from .orientation import Orientation
from .qtiboolean import QtiBoolean
from .qtiinteger import QtiInteger
from .qtistring import QtiString
from .string256 import String256

class_dict = {
    'Generic': Generic,
    'Language': Language,
    'QtiBoolean': QtiBoolean,
    'QtiString': QtiString,
    'QtiInteger': QtiInteger,
    'String256': String256,
    'IdentifierResponse': IdentifierResponse,
    'Orientation': Orientation,
    'Length': Length,
}


def create_attribute_type_class_object(type_name, value):
    cls = class_dict.get(type_name)
    if cls:
        return cls(value)
    return None


def is_valid_attribute_type_class(type_class_name):
    return class_dict.get(type_class_name) is not None


def get_attribute_type_class(type_class_name):
    return class_dict.get(type_class_name)
