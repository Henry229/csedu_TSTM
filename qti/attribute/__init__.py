
from .adaptive import Adaptive
from .data import Data
from .height import Height
from .label import Label
from .lang import Lang
from .maxchoices import MaxChoices
from .minchoices import MinChoices
from .orientation import Orientation
from .responseidentifier import ResponseIdentifier
from .shuffle import Shuffle
from .timedependent import TimeDependent
from .title import Title
from .toolname import ToolName
from .toolversion import ToolVersion
from .width import Width

class_dict = {
    'Title': Title,
    'Label': Label,
    'Lang': Lang,
    'Adaptive': Adaptive,
    'TimeDependent': TimeDependent,
    'ToolName': ToolName,
    'ToolVersion': ToolVersion,
    'ResponseIdentifier': ResponseIdentifier,
    'MinChoices': MinChoices,
    'MaxChoices': MaxChoices,
    'Orientation': Orientation,
    'Shuffle': Shuffle,
    'Width': Width,
    'Height': Height,
    'Data': Data,
}


def create_attribute_class_object(class_name, value=None, version=''):
    cls = class_dict.get(class_name)
    if cls:
        return cls(value, version)
    return None


def get_attribute_class(class_name):
    return class_dict.get(class_name)


def is_valid_attribute_class(class_name):
    return class_dict.get(class_name) is not None
