from .attributetype import AttributeType


class String256(AttributeType):
    @classmethod
    def validate(cls, value):
        return type(value) is str and len(value) <= 256

    @classmethod
    def fix(cls, value):
        fixed = str(value)[:253] + '...'
        return fixed
