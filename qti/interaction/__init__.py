from .associateinteraction import AssociateInteraction
from .choiceinteraction import ChoiceInteraction
from .extendedtextinteraction import ExtendedTextInteraction
from .gapmatchinteraction import GapMatchInteraction
from .graphicgapmatchinteraction import GraphicGapMatchInteraction
from .hotspotinteraction import HotspotInteraction
from .hottextinteraction import HottextInteraction
from .inlinechoiceinteraction import InlineChoiceInteraction
from .matchinteraction import MatchInteraction
from .mediainteraction import MediaInteraction
from .objectinteraction import ObjectInteraction
from .orderinteraction import OrderInteraction
from .textentryinteraction import TextEntryInteraction
from .uploadinteraction import UploadInteraction

class_dict = {
    'ChoiceInteraction': ChoiceInteraction,
    'ObjectInteraction': ObjectInteraction,
    'GraphicGapMatchInteraction': GraphicGapMatchInteraction,
    'InlineChoiceInteraction': InlineChoiceInteraction,
    'HottextInteraction': HottextInteraction,
    'TextEntryInteraction': TextEntryInteraction,
    'MediaInteraction': MediaInteraction,
    'OrderInteraction': OrderInteraction,
    'MatchInteraction': MatchInteraction,
    'AssociateInteraction': AssociateInteraction,
    'HotspotInteraction': HotspotInteraction,
    'ExtendedTextInteraction': ExtendedTextInteraction,
    'GapMatchInteraction': GapMatchInteraction,
    'UploadInteraction': UploadInteraction,
}


def create_interaction_class_object(class_name, attributes=None, related_item=None, serial=''):
    cls = class_dict.get(class_name)
    if cls:
        return cls(attributes, related_item, serial)
    return None


def get_interaction_class(class_name):
    return class_dict.get(class_name)


def is_valid_interaction_class(class_name):
    return class_dict.get(class_name) is not None
