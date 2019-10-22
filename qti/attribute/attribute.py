from ..attributetype import is_valid_attribute_type_class, create_attribute_type_class_object, get_attribute_type_class


class Attribute:
    QTI_v2p0 = '2.0'
    QTI_v2p1 = '2.1'

    name = ''
    type = ''
    required = False
    defaultValue = None
    appDefaultValue = None

    def __init__(self, value=None, version=''):
        self.version = version if version != '' else self.QTI_v2p1
        self.value = None
        if self.name == '' or self.type == '':
            raise ValueError()

        if is_valid_attribute_type_class(self.type):
            if value is not None:
                self.value = create_attribute_type_class_object(self.type, value)
            elif self.defaultValue is not None:
                self.value = create_attribute_type_class_object(self.type, self.defaultValue)
            elif self.appDefaultValue is not None:
                self.value = create_attribute_type_class_object(self.type, self.appDefaultValue)
        else:
            raise ValueError()

    def __str__(self):
        return str(self.value) if self.value is not None else ''

    def is_required(self):
        return self.required

    def is_none(self):
        return self.value is None

    def set_none(self):
        self.value = None

    def validate_value(self, value):
        valid = False
        cls = get_attribute_type_class(self.type)
        if cls is not None:
            valid = getattr(cls, 'validate')(value)
        return valid

    def validate_cardinality(self):
        if self.required:
            return self.value is not None
        return True

    def get_name(self):
        return self.name

    def get_type(self):
        return self.type

    def get_default(self):
        return self.defaultValue

    def get_value(self, return_obj=False):
        value = None
        if self.value is not None:
            if return_obj:
                value = self.value
            else:
                value = self.value.get_value()
        return value

    def set_value(self, value):
        if value is not None:
            value = create_attribute_type_class_object(self.type, value)
            if value is not None:
                self.value = value
            else:
                raise ValueError("type is not supported.")





