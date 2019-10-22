from .inlineinteraction import InlineInteraction


class InlineChoiceInteraction(InlineInteraction):
    qtiTagName = 'inlineChoiceInteraction'
    choiceClass = 'InlineChoice'
    baseType = 'identifier'

    # @staticmethod
    # def get_template_qti():
    #     return ''

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Shuffle', 'Required'
        ]

    @classmethod
    def get_template_qti(cls):
        tpl_name = 'interactions/blockinteraction.xml'
        return tpl_name

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        choices = []
        for choice in self.get_choices().values():
            choices.append(choice.to_html(self))
        variables['choices'] = choices
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/inlinechoiceinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
