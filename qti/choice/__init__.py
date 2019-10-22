from .associablehotspot import AssociableHotspot
from .choice import Choice
from .containerchoice import ContainerChoice
from .gap import Gap
from .gapimg import GapImg
from .gaptext import GapText
from .hotspotchoice import HotspotChoice
from .hottext import Hottext
from .inlinechoice import InlineChoice
from .simpleassociablechoice import SimpleAssociableChoice
from .simplechoice import SimpleChoice
from .textvariablechoice import TextVariableChoice

class_dict = {
    'Choice': Choice,
    'SimpleChoice': SimpleChoice,
    'TextVariableChoice': TextVariableChoice,
    'GapImg': GapImg,
    'InlineChoice': InlineChoice,
    'Hottext': Hottext,
    'SimpleAssociableChoice': SimpleAssociableChoice,
    'HotspotChoice': HotspotChoice,
    'GapText': GapText,
    'Gap': Gap,
    'AssociableHotspot': AssociableHotspot
}


def create_choice_class_object(class_name, attributes=None, related_item=None, serial=''):
    cls = class_dict.get(class_name)
    if cls:
        return cls(attributes, related_item, serial)
    return None


def get_choice_class(class_name):
    return class_dict.get(class_name)


def is_valid_choice_class(class_name):
    return class_dict.get(class_name) is not None
