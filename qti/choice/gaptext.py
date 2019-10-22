from .containerchoice import ContainerChoice


class GapText(ContainerChoice):
    qtiTagName = 'gapText'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'MatchMax', 'MatchMin'
        ]

    def to_html(self, interaction=None):
        template = self.get_template_html()
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
