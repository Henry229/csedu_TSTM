from ..choice.containerchoice import ContainerChoice


class Hottext(ContainerChoice):
    qtiTagName = 'hottext'

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['body'] = self.get_content()
        return variables

    def to_html(self, interaction=None):
        template = 'choices/hottext.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
