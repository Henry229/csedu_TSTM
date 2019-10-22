from .choice import Choice
from ..container.containerstatic import ContainerStatic
from ..container.flowcontainer import FlowContainerMixin


class ContainerChoice(FlowContainerMixin, Choice):
    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.body = ContainerStatic()

    def get_body(self):
        return self.body

    def set_content(self, content):
        self.get_body().edit(content)

    def get_content(self):
        return self.get_body().get_body()

    def get_template_html(self):
        template = 'choices/' + self.__class__.__name__.lower() + '.html'
        return template

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': is not implemented')
