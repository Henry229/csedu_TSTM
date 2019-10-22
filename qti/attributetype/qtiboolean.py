from .attributetype import AttributeType


class QtiBoolean(AttributeType):
    @classmethod
    def validate(cls, value):
        return type(value) is bool

    @classmethod
    def fix(cls, value):
        fixed = None
        if value.lower() == 'false':
            fixed = False
        else:
            try:
                fixed = bool(value)
            except ValueError:
                pass
        return fixed
