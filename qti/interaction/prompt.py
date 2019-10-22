
from jinja2 import Template

from ..container.containerstatic import ContainerStatic
from ..container.flowcontainer import FlowContainerMixin
from ..element import Element


class Prompt(FlowContainerMixin, Element):
    qtiTagName = 'prompt'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.body = ContainerStatic('', related_item)

    def get_body(self):
        return self.body

    def get_used_attributes(self):
        return {}

    def to_html(self, interaction=None):
        body_variables = {}
        html_rendered = str(self.body)
        for name, element in self.body.get_elements().items():
            body_variables[name] = element.to_html()
        if len(body_variables) > 0:
            tpl = Template(html_rendered)
            html_rendered = tpl.render(body_variables)
        return html_rendered

