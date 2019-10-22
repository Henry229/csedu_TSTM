from .attributetype import AttributeType
from ..utils import ClassUtils


class Identifier(AttributeType):
    @classmethod
    def validate(cls, value):
        return Identifier.fix(value) is not None

    @staticmethod
    def check_identifier(identifier):
        return True

    @classmethod
    def fix(cls, value):
        return_value = None

        for cls_name in Identifier.get_allowed_classes():
            if ClassUtils.is_subclass_by_name(value, cls_name):
                return_value = True
                break
        return return_value

    @staticmethod
    def get_allowed_classes():
        return ['IdentifiedElement']

    def get_value(self):
        value = None
        if self.value is not None:
            value = self.value.get_identifier()

        return value

    def get_referenced_object(self):
        if self.value is not None:
            return self.value
        return None

