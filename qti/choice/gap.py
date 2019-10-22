from ..choice.choice import Choice


class Gap(Choice):
    qtiTagName = 'gap'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Required'
        ]

    def set_content(self, content):
        raise ValueError("set_content not supported.")

    def get_content(self):
        raise ValueError("get_content not supported.")

    def to_html(self, interaction=None):
        template = self.get_template_html()
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
