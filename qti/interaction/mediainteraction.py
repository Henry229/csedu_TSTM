from .objectinteraction import ObjectInteraction


class MediaInteraction(ObjectInteraction):
    qtiTagName = 'mediaInteraction'
    choiceClass = ''
    baseType = 'integer'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Autostart', 'MinPlays', 'MaxPlays', 'Loop'
        ]

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        return variables

    def get_object_variables(self):
        obj = self.get_object()
        related_item = self.get_related_item()
        variables = {
            'obj': {
                'width': obj.get_attribute_value('width'),
                'height': obj.get_attribute_value('height'),
                'type': obj.get_attribute_value('type'),
                'data': '/itemstatic/img/' + related_item.get_resource_id() + '/' + obj.get_attribute_value('data')
            },
        }
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/mediainteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
