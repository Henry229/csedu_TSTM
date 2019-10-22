from .blockinteraction import BlockInteraction
from ..itemrenderer.itemrenderer import ItemRenderer


class OrderInteraction(BlockInteraction):
    qtiTagName = 'orderInteraction'
    choiceClass = 'SimpleChoice'
    baseType = 'identifier'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Shuffle', 'MaxChoicesOrderInteraction', 'MinChoicesOrderInteraction',
            'Orientation'
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
        template = 'interactions/orderinteraction.html'
        variables = self.get_template_html_variables()
        tpl_renderer = ItemRenderer(template, variables)
        html_rendered = tpl_renderer.render()
        return html_rendered
