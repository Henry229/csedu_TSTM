from .element import Element
from .itemrenderer.itemrenderer import ItemRenderer


class Img(Element):
    qtiTagName = 'img'

    def get_used_attributes(self):
        return [
            'Src', 'Alt', 'Width', 'Height'
        ]

    def to_html(self, interaction=None):
        template = 'element.html'
        variables = self.get_template_qti_variables()
        if 'attributes' in variables:
            if 'src' in variables['attributes']:
                src = variables['attributes']['src']
                related_item = self.get_related_item()
                variables['attributes']['src'] = '/itemstatic/img/' + related_item.get_resource_id() + '/' + src
            variables['attributes'] = self.xmlize_options(variables['attributes'], True)
        tpl_renderer = ItemRenderer(template, variables)
        html_rendered = tpl_renderer.render()
        return html_rendered
