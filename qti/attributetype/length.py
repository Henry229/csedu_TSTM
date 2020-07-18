from .attributetype import AttributeType


class Length(AttributeType):
    @classmethod
    def validate(cls, value):
        if type(value) is int:
            return True
        if type(value) is str:
            val = value.replace('%', '')
            try:
                val = int(val)
                return True
            except ValueError:
                pass
        return False

    @classmethod
    def fix(cls, value):
        val = value.replace('%', '')
        try:
            fixed = int(val)
        except Exception:
            fixed = None
        return fixed
