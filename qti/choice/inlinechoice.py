from .textvariablechoice import TextVariableChoice


class InlineChoice(TextVariableChoice):
    qtiTagName = 'inlineChoice'

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['body'] = self.get_content()
        return variables

    def to_html(self, interaction=None):
        template = 'choices/inlinechoice.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
