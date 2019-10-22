from .attributetype import AttributeType


class Enumeration(AttributeType):
    @classmethod
    def validate(cls, value):
        return value in cls.get_enumeration()

    @classmethod
    def fix(cls, value):
        enums = cls.get_enumeration()
        fixed = None
        for enum in enums:
            if value.lower() == enum.lower():
                fixed = enum
                break
        return fixed

    @staticmethod
    def get_enumeration():
        raise NotImplementedError()

    def set_value(self, value):
        if value:
            super().set_value(value)
