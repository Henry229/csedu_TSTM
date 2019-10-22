from .element import Element


class Object(Element):
    qtiTagName = 'object'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.alt = None

    def get_used_attributes(self):
        return [
            'Data', 'Type', 'Width', 'Height'
        ]

    def set_alt(self, obj):
        if isinstance(obj, Object) or isinstance(obj, str):
            self.alt = obj

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        if self.alt is not None:
            if isinstance(self.alt, Object):
                variables['_alt'] = self.alt.to_qti()
            else:
                variables['_alt'] = str(self.alt)
        return variables

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        if self.alt is not None:
            if isinstance(self.alt, Object):
                data['_alt'] = self.alt.to_dict(filter_variable_content, filtered)
            else:
                data['_alt'] = str(self.alt)
        return data

