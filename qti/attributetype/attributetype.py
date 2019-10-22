
class AttributeType:
    def __init__(self, value=None):
        self.value = None
        self.set_value(value)

    def __str__(self):
        return self.get_value()

    def get_value(self):
        value = None
        if self.value is not None:
            value = self.value
        return value

    def self_check(self):
        return self.validate(self.value)

    @classmethod
    def validate(cls, value):
        raise NotImplementedError()

    @classmethod
    def fix(cls, value):
        raise NotImplementedError()

    def set_value(self, value):
        if self.validate(value):
            self.value = value
        elif self.fix(value) is not None:
            self.value = self.fix(value)
        else:
            raise ValueError()
