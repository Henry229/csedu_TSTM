from .blockinteraction import BlockInteraction


class ExtendedTextInteraction(BlockInteraction):
    qtiTagName = 'extendedTextInteraction'
    choiceClass = ''
    baseType = 'string'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Base', 'StringIdentifier', 'ExpectedLength', 'PatternMask', 'PlaceholderText',
            'MaxStrings', 'MinStrings', 'ExpectedLines', 'Format',
        ]

    def get_base_type(self):
        base_type = super().get_base_type()

        response = self.get_response()
        if response is not None:
            authorized_base_type = ['string', 'integer', 'float']
            base_t = response.get_attribute_values('baseType').lower()
            if base_t in authorized_base_type:
                base_type = base_t

        return base_type

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/extendedtextinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
