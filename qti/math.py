from .element import Element


class Math(Element):
    qtiTagName = 'math'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.mathML = ''
        self.annotations = {}

    def set_mathml(self, mathml):
        ns = self.get_math_namespace()
        mathml = mathml
        if ns:
            mathml = mathml
        self.mathML = mathml

    def get_mathml(self):
        return self.mathML

    def get_used_attributes(self):
        return {}

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()

        # ToDo: not implemented
        return variables

    def get_math_namespace(self):
        ns = ''
        related_item = self.get_related_item()
        if related_item is not None:
            for name, uri in related_item.get_namepalces().items():
                if 'MathML' in uri:
                    ns = name
                    break
        return ns

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['mathML'] = self.mathML
        data['annotations'] = self.annotations
        return data

    def get_annotations(self):
        return self.annotations

    def set_annotations(self, annotations):
        self.annotations = annotations

    def set_annotation(self, encoding, value):
        self.annotations[encoding] = value

    def remove_annotation(self, encoding):
        del self.annotations['encoding']

