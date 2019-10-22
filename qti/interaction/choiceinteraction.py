from .blockinteraction import BlockInteraction


class ChoiceInteraction(BlockInteraction):
    qtiTagName = 'choiceInteraction'
    choiceClass = 'SimpleChoice'
    baseType = 'identifier'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Shuffle', 'MaxChoices', 'MinChoices', 'Orientation'
        ]

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        choices = []
        for choice in self.get_choices().values():
            choices.append(choice.to_html(self))
        variables['choices'] = choices
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/choiceinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered

