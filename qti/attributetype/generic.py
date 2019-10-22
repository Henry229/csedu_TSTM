
from .attributetype import AttributeType


class Generic(AttributeType):
    @classmethod
    def validate(cls, value):
        return True

    @classmethod
    def fix(cls, value):
        return str(value)
