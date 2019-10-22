from .containerchoice import ContainerChoice


class SimpleChoice(ContainerChoice):
    qtiTagName = 'simpleChoice'

    def to_html(self, interaction=None):
        template = self.get_simple_choice_template_html(interaction)
        variables = self.get_template_html_variables()
        variables['interaction'] = interaction
        cardinality = self.relatedItem.get_cardinality()
        variables['unique'] = cardinality == 'single'
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered

    def get_simple_choice_template_html(self, interaction):
        if interaction is not None:
            if interaction.__class__.__name__ == 'OrderInteraction':
                template = 'choices/choice.html'
                return template
        template = super().get_template_html()
        return template
