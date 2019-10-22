from .containerinteraction import ContainerInteraction


class HottextInteraction(ContainerInteraction):
    qtiTagName = 'hottextInteraction'
    choiceClass = 'Hottext'
    containerType = 'ContainerHottext'
    baseType = 'identifier'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'MaxChoices', 'MinChoices'
        ]

    def add_choice(self, choice):
        raise ValueError()

    def create_choice(self, choice_attributes=None, choice_value=None):
        raise ValueError()

    def remove_choice(self, choice, set_number=None):
        return self.body.remove_element(choice)

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        del variables['choices']

        return variables

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        if 'choices' in data:
            del data['choices']
        return data

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/hottextinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
