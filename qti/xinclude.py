from .container.containerstatic import ContainerStatic
from .container.flowcontainer import FlowContainerMixin
from .element import Element


class XInclude(FlowContainerMixin, Element):
    qtiTagName = 'include'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.body = ContainerStatic('', related_item)

    def get_body(self):
        return self.body

    def get_used_attributes(self):
        return []

    def get_template_qti_variables(self):
        variable = super().get_template_qti_variables()

        # ToDo : not implemented
        return variable

    def get_xinclude_namespace(self):
        ns = ''
        related_item = self.get_related_item()
        if related_item is not None:
            for name, uri in related_item.get_namespaces().items():
                if 'XInclude' in uri:
                    ns = name
                    break

        return ns

    @classmethod
    def get_template_qti(cls):
        return cls.get_template_path() + 'xinclude.xml'
