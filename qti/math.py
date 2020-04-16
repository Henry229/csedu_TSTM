from .element import Element
from .renderer.templaterendere import TemplateRenderer


class Math(Element):
    qtiTagName = 'math'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.mathML = ''
        self.annotations = {}

    def set_mathml(self, mathml):
        import re
        ns = self.get_math_namespace()
        # strip the outer math tags, to only store the body
        # mathml = mathml
        if ns:
            mathml = re.sub(r'<\s*\w*:', "<", mathml, flags=re.IGNORECASE)
            mathml = re.sub(r'</\s*\w*:', "</", mathml, flags=re.IGNORECASE)
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
            for name, uri in related_item.get_namespaces().items():
                if 'MathML' in uri:
                    ns = name
                    break
        return ns

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['mathML'] = self.mathML
        data['annotations'] = self.annotations
        return data

    def get_template_qti_variables(self):
        import re
        variables = super().get_template_qti_variables()

        tag = self.qtiTagName
        body = self.mathML

        annotations = ''
        for encoding, value in self.annotations.items():
            annotations += '<annotation encoding="' + encoding + '">' + value + '</annotation>'

        if annotations != '':
            if '</semantics>' in body:
                body = body.replace('</semantics>', annotations + '</semantics>')
            else:
                body = '<semantics>' + body + annotations + '</semantics>'

        ns = self.get_math_namespace()
        if ns == '':
            related_item = self.relatedItem
            if related_item is not None:
                ns = 'm'
                related_item.add_namespace(ns, 'http://www.w3.org/1998/Math/MathML')

        if ns != '':
            body = re.sub(r'<(?!/)(?!!)', "<" + ns + ":", body, flags=re.IGNORECASE)
            body = re.sub(r'</', "</" + ns + ":", body, flags=re.IGNORECASE)
            tag = ns + ":" + tag

        variables['tag'] = tag
        variables['body'] = body
        return variables

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['raw'] = self.mathML
        return variables

    def to_html(self, interaction=None):
        template = 'math.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered

    def get_annotations(self):
        return self.annotations

    def set_annotations(self, annotations):
        self.annotations = annotations

    def set_annotation(self, encoding, value):
        self.annotations[encoding] = value

    def remove_annotation(self, encoding):
        del self.annotations['encoding']

