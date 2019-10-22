from .blockinteraction import BlockInteraction
from ..objectelement import Object


class ObjectInteraction(BlockInteraction):
    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.object = Object()

    def set_object(self, obj):
        self.object = obj

    def get_object(self):
        return self.object

    def to_dict(self, filter_variable_content=False, filtered=None):
        value = super().to_dict(filter_variable_content, filtered)
        value['object'] = self.object.to_dict(filter_variable_content, filtered)
        return value

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['object'] = self.object.to_qti()
        return variables

    def get_object_variables(self):
        obj = self.get_object()
        choices = []
        for choice in self.choices.values():
            coords = [int(c) for c in choice.get_attribute_value('coords').split(',')]
            var = {
                'shape': choice.get_attribute_value('shape'),
                'identifier': choice.get_identifier()
            }
            if choice.get_attribute_value('shape') == 'ellipse':
                var['cx'], var['cy'], var['rx'], var['ry'] = coords
            else:
                var['x'] = coords[0]
                var['y'] = coords[1]
                var['width'] = coords[2] - coords[0]
                var['height'] = coords[3] - coords[1]
            choices.append(var)
        related_item = self.get_related_item()
        variables = {
            'obj': {
                'width': obj.get_attribute_value('width'),
                'height': obj.get_attribute_value('height'),
                'data': '/itemstatic/img/' + related_item.get_resource_id() + '/' + obj.get_attribute_value('data')
            },
            'choices': choices
        }
        return variables

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': to_html is not implemented')
