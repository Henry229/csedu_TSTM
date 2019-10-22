from .container import Container
from ..element import Element


class ContainerInteractive(Container):
    def after_element_set(self, qti_element: Element):
        pass

    def after_element_remove(self, qti_element: Element):
        pass
