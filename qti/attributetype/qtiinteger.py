from .attributetype import AttributeType


class QtiInteger(AttributeType):
    @classmethod
    def validate(cls, value):
        return type(value) is int

    @classmethod
    def fix(cls, value):
        fixed = int(value)
        return fixed
