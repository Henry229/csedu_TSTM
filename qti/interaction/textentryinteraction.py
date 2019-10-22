from .inlineinteraction import InlineInteraction


class TextEntryInteraction(InlineInteraction):
    qtiTagName = 'textEntryInteraction'
    choiceClass = ''
    baseType = 'string'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Base', 'StringIdentifier', 'ExpectedLength', 'PatternMask', 'PlaceholderText'
        ]

    def get_base_type(self):
        base_type = super().get_base_type()

        response = self.get_response()
        if response is not None:
            authorized_base_type = ['string', 'integer', 'float']
            base = response.get_attribute_value('baseType').lower()
            if base in authorized_base_type:
                base_type = base

        return base_type

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/textentryinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
