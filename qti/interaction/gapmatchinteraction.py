from .containerinteraction import ContainerInteraction
from ..choice.gap import Gap


class GapMatchInteraction(ContainerInteraction):
    qtiTagName = 'gapMatchInteraction'
    choiceClass = 'GapText'
    baseType = 'directedPair'
    containerType = 'ContainerGap'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Shuffle'
        ]

    def get_gaps(self):
        return self.get_body().get_elements('Gap')

    def remove_gap(self, gap):
        return self.body.remove_element(gap)

    def get_identified_elements(self):
        elements = super().get_identified_elements()
        elements.add_multiple(self.get_gaps())
        return elements

    def get_choice_by_serial(self, serial):
        choice = super().get_choice_by_serial(serial)
        if choice is None:
            gaps = self.get_gaps()
            if serial in gaps:
                choice = gaps[serial]
        return choice

    def remove_choice(self, choice, set_number=None):
        if isinstance(choice, Gap):
            return self.body.remove_element(choice)
        else:
            super().remove_choice(choice)

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        choices = []
        for choice in self.get_choices().values():
            choices.append(choice.to_html(self))
        variables['choices'] = choices
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/gapmatchinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
