from .container import Container
from ..choice.hottext import Hottext
from ..element import Element


class ContainerHottext(Container):
    def get_valid_element_types(self):
        return [
            'Img', 'Math', 'Table', 'Feedback', 'Object',
            'Hottext'
        ]

    def after_element_set(self, qti_element: Element):
        super().after_element_set(qti_element)
        if isinstance(qti_element, Hottext):
            item = self.get_related_item()
            if item is not None:
                qti_element.set_related_item(item)