from .containerchoice import ContainerChoice


class SimpleAssociableChoice(ContainerChoice):
    qtiTagName = 'simpleAssociableChoice'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'MatchMax', 'MatchMin'
        ]

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        return variables

    def get_template_html(self, interaction=None):
        template = ''
        if interaction is not None:
            if interaction.__class__.__name__ == 'MatchInteraction' \
                    or interaction.__class__.__name__ == 'ChoiceInteraction':
                template = 'choices/' + self.__class__.__name__.lower() \
                           + interaction.__class__.__name__.lower() + '.html'
        if template == '':
            template = 'choices/choice.html'
        return template

    def to_html(self, interaction=None):
        template = self.get_template_html(interaction)
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
