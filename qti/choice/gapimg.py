from ..choice.choice import Choice
from ..objectelement import Object


class GapImg(Choice):
    qtiTagName = 'gapImg'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.object = Object()

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'ObjectLabel'
        ]

    def set_content(self, content):
        if isinstance(content, Object):
            self.set_object(content)
        else:
            raise ValueError()

    def get_content(self):
        return self.get_object()

    def set_object(self, img_object):
        self.object = img_object

    def get_object(self):
        return self.object

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['body'] = self.object.to_qti()
        return variables

    def to_dict(self, filter_variable_content=False, filtered=None):
        value = super().to_dict(filter_variable_content, filtered)
        value['object'] = self.object.to_dict(filter_variable_content, filtered)
        return value

    def to_html(self, interaction=None):
        template = self.get_template_html()
        variables = self.get_template_html_variables()
        src = self.object.attributes['data']
        related_item = self.get_related_item()
        src = '/itemstatic/img/' + related_item.get_resource_id() + '/' + src.get_value()
        variables['img'] = {
            'src': src,
            'width': self.object.get_attribute_value('width'),
            'height': self.object.get_attribute_value('height')
        }
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
