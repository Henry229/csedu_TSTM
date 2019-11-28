from .blockinteraction import BlockInteraction


class UploadInteraction(BlockInteraction):
    qtiTagName = 'uploadInteraction'
    choiceClass = ''
    baseType = 'file'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'TypeUploadInteraction'
        ]

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/extendedtextinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
