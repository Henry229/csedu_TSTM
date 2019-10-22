from .blockinteraction import BlockInteraction
from ..container import is_valid_container_class, create_container_class_object
from ..container.flowcontainer import FlowContainerMixin


class ContainerInteraction(FlowContainerMixin, BlockInteraction):
    containerType = ''

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        if is_valid_container_class(self.containerType):
            self.body = create_container_class_object(self.containerType, related_item)
        else:
            raise ValueError("The container class is not supported.")

    def get_body(self):
        return self.body

    # @staticmethod
    # def get_template_qti():
    #     return ''

