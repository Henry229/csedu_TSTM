from .attributetype import AttributeType


class Language(AttributeType):
    @classmethod
    def validate(cls, value):
        return True

    @classmethod
    def fix(cls, value):
        return value
