from jinja2 import Template

from ..element import Element
from ..identifiedelement import IdentifiedElement
from ..identifiedelementcontainer import IdentifiedElementContainerMixin
from ..identifiercollection import IdentifierCollection
from ..utils import ClassUtils


class Container(IdentifiedElementContainerMixin, Element):
    def __init__(self, body='', related_item=None, serial=''):
        super().__init__({}, related_item, serial)
        self.body = body
        self.elements = {}

    def __str__(self):
        return self.body

    def get_used_attributes(self):
        return []

    def set_element(self, qti_element: Element, body='', integrity_check=True, required_placeholder=True):
        self.set_elements({qti_element.get_serial(): qti_element}, body, integrity_check, required_placeholder)

    def set_elements(self, qti_elements, body='', integrity_check=True, required_placeholder=True):
        missing_elements = {}
        if integrity_check and body != '':
            if not self.check_integrity(body, missing_elements):
                return False

        if body == '':
            body = self.body

        for qti_element in qti_elements.values():
            if not self.is_valid_element(qti_element):
                raise ValueError()

            place_holder = qti_element.get_placeholder()
            if place_holder not in body:
                if required_placeholder:
                    raise ValueError("place_holder not in body")
                else:
                    body = body + place_holder
            related_item = self.get_related_item()
            if related_item is not None:
                qti_element.set_related_item(related_item)
                if isinstance(qti_element, IdentifiedElement):
                    qti_element.get_identifier()
            self.elements[qti_element.get_serial()] = qti_element
            self.after_element_set(qti_element)

        self.edit(body)

        return True

    def after_element_set(self, qti_element: Element):
        if isinstance(qti_element, IdentifiedElement):
            pass

    def after_element_remove(self, qti_element: Element):
        pass

    def get_body(self):
        return self.body

    def edit(self, body, integrity_check=False):
        if not isinstance(body, str):
            raise ValueError()

        if integrity_check and not self.check_integrity(body):
            return False

        self.body = body
        return True

    def check_integrity(self, body, missing_elements: dict = None):
        return_value = True
        for element in self.elements.values():
            if element.get_placeholder() not in body:
                return_value = False
                if missing_elements is not None:
                    missing_elements[element.get_serial()] = element
                else:
                    break
        return return_value

    @staticmethod
    def fix_non_void_tags(html):
        # ToDo: not implemented
        return html

    def is_valid_element(self, element: Element):
        valid_classes = self.get_valid_element_types()
        for cls in valid_classes:
            if ClassUtils.is_subclass_by_name(element, cls):
                return True
        return False

    def get_valid_element_types(self):
        raise NotImplementedError()

    def get_element(self, serial: str):
        return self.elements.get(serial)

    def get_elements(self, class_name=''):
        """
        Return  self.elements if class_name is ''
        Return elements filtered with class_name if class_name is not ''
        :param class_name:
        :return:
        """
        elements = {}
        if class_name != '':
            for serial, element in self.elements.items():
                if ClassUtils.is_subclass_by_name(element, class_name):
                    elements[serial] = element
        else:
            elements = self.elements
        return elements

    def remove_element(self, element):
        serial = ''
        if isinstance(element, Element):
            serial = element.get_serial()
        elif type(element) is str:
            serial = element

        if serial != '' and serial in self.elements:
            self.body = self.body.replace(self.elements[serial].get_placeholder(), '')
            self.after_element_remove(self.elements['serial'])
            del self.elements[serial]
            return True
        return False

    def replace_element(self, old_element: Element, new_element: Element):
        body = self.body.replace(old_element.get_placeholder(), new_element.get_placeholder())
        self.remove_element(old_element)
        self.set_element(new_element, body)

    def get_identified_elements(self):
        element_collection = IdentifierCollection()
        for ele in self.elements:
            if isinstance(ele, IdentifiedElementContainerMixin):
                element_collection.merge(ele.get_identified_elements())
            if isinstance(ele, IdentifiedElement):
                element_collection.add(ele)
        return element_collection

    def to_qti(self):
        value = self.get_body()
        for element in self.elements.values():
            value = value.replace(element.get_placeholder(), element.to_qti())
        return value

    def to_dict(self, filter_variable_content=False, filtered=None):
        import os

        if filtered is None:
            filtered = {}
        data = {
            'serial': self.get_serial(),
            'body': self.get_body(),
            'elements': self.get_dict_serialized_element_collection(self.get_elements(),
                                                                    filter_variable_content, filtered)
        }

        if os.environ.get("DEBUG", 'false') == 'true':
            data['debug'] = {
                'relatedItem': self.get_related_item().get_serial() if self.get_related_item() is not None else ''
            }
        return data

    def to_html(self, interaction=None):
        body_variables = {}
        html_rendered = str(self.body)
        for name, element in self.get_elements().items():
            body_variables[name] = element.to_html(interaction)
        if len(body_variables) > 0:
            tpl = Template(html_rendered)
            html_rendered = tpl.render(body_variables)
        return html_rendered

