from .attributetype import AttributeType


class QtiString(AttributeType):
    @classmethod
    def validate(cls, value):
        return type(value) is str

    @classmethod
    def fix(cls, value):
        fixed = str(value)
        return fixed
