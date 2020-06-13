import html
import os

from .attribute import is_valid_attribute_class, create_attribute_class_object
from .attribute.responseidentifier import ResponseIdentifier
from .attributetype import get_attribute_type_class, create_attribute_type_class_object
from .attributetype.identifier import Identifier
from .container.flowcontainer import FlowContainerMixin
from .exportable import Exportable
from .itemrenderer.itemrenderer import ItemRenderer
from .renderer.templaterendere import TemplateRenderer


class Element(Exportable):
    instances = {}
    templatePath = ''
    qtiTagName = ''

    def __init__(self, attributes=None, related_item=None, serial=''):
        if attributes is None:
            attributes = {}
        # Set properties with default values
        self.serial = ''
        self.relatedItem = None
        self.attributes = {}

        if related_item is not None:
            self.set_related_item(related_item)
        if serial != '':
            if self.instances.get(serial) is not None:
                raise ValueError("serial must be unique")
            else:
                self.serial = serial
        else:
            self.serial = self.build_serial()
        self.reset_attributes()
        self.set_attributes(attributes)
        self.instances[self.get_serial()] = self

    def get_qti_tag(self):
        return self.qtiTagName

    def get_used_attributes(self):
        raise NotImplementedError()

    def reset_attributes(self):
        self.attributes = {}
        for attrClass in self.get_used_attributes():
            if is_valid_attribute_class(attrClass):
                attribute = create_attribute_class_object(attrClass)
                self.attributes[attribute.name] = attribute

    def set_attributes(self, attributes: dict):
        for name, value in attributes.items():
            self.set_attribute(name, value)

    def set_attribute(self, name, value):
        from .identifiedelement import IdentifiedElement

        result = False
        if value is None:
            return result

        if name in self.attributes:
            # get datatype name
            datatype_name = self.attributes[name].get_type()
            datatype_cls = get_attribute_type_class(datatype_name)
            if issubclass(datatype_cls, Identifier):
                if isinstance(value, IdentifiedElement):
                    if self.validate_attribute(name, value):
                        self.attributes[name].set_value(value)
                        result = True
                    else:
                        raise ValueError()
                elif isinstance(value, str):
                    identifier = value
                    element = self.get_identified_element(identifier, datatype_cls.get_allowed_classes())
                    if element is not None:
                        self.attributes[name].set_value(element)
                        result = True
            else:
                self.attributes[name].set_value(value)
                result = True
        else:
            self.attributes[name] = create_attribute_type_class_object('Generic', value)
            result = True
        return result

    def validate_attribute(self, name, value=None):
        from .identifiedelement import IdentifiedElement

        valid = False
        if self.attributes.get(name):
            if value is None:
                value = self.attributes[name].get_value()

            datatype_class_name = self.attributes[name].get_type()
            datatype_class = get_attribute_type_class(datatype_class_name)
            if issubclass(datatype_class, Identifier):
                if datatype_class.validate(value):
                    related_item = self.get_related_item()
                    if related_item is not None:
                        id_collection = related_item.get_identified_elements()
                        if isinstance(value, IdentifiedElement) and id_collection.exist(value.get_identifier()):
                            valid = True
                    else:
                        raise ValueError()
            else:
                valid = datatype_class.validate(value)
        else:
            raise ValueError()

        return valid

    def get_attribute(self, name):
        return self.attributes.get(name)

    def get_attribute_value(self, name):
        if name in self.attributes:
            return self.attributes[name].get_value()
        return None

    def get_attribute_values(self, filter_none=True):
        values = {}
        for name, attribute in self.attributes.items():
            if not filter_none or attribute.value is not None:
                values[name] = attribute.get_value()
        return values

    def get_placeholder(self):
        return "{{" + self.get_serial() + "}}"

    @staticmethod
    def get_template_path():
        if Element.templatePath is '':
            base_dir = os.path.abspath(os.path.dirname(__file__))
            Element.templatePath = os.path.join(base_dir, 'renderer/templates')
        return Element.templatePath

    @classmethod
    def get_template_qti(cls):
        template_path = cls.get_template_path()
        tpl_name = 'qti' + cls.qtiTagName.lower() + '.xml'
        template = os.path.join(template_path, tpl_name)
        if not os.path.exists(template):
            tpl_name = 'qtielement.xml'
        return tpl_name

    def get_template_qti_variables(self):
        variables = {
            'tag': self.qtiTagName,
            'attributes': self.get_attribute_values()
        }
        if isinstance(self, FlowContainerMixin):
            variables['body'] = self.get_body().to_qti()

        return variables

    def get_template_html_variables(self):
        variables = {
            'tag': self.qtiTagName,
            'serial': self.get_serial(),
            'attributes': self.get_attribute_values()
        }
        is_horizontal = variables['attributes'].get('orientation', 'vertical') == 'horizontal'
        variables['horizontal'] = is_horizontal
        if isinstance(self, FlowContainerMixin):
            variables['body'] = self.get_body().to_html(self.relatedItem)

        return variables

    def add_class(self, class_name):
        old_name = self.get_attribute('class')
        old_classes = old_name.split() if old_name else []
        new_classes = old_classes + class_name.split()
        self.set_attribute('class', ' '.join(new_classes))

    def remove_class(self, class_name):
        old_name = self.get_attribute('class')
        old_classes = old_name.split() if old_name else []
        new_classes = [cls for cls in old_classes if class_name != cls]
        self.set_attribute('class', ' '.join(new_classes))

    def to_qti(self):
        template = self.get_template_qti()
        variables = self.get_template_qti_variables()
        if 'attributes' in variables:
            variables['attributes'] = self.xmlize_options(variables['attributes'], True)
        tpl_renderer = TemplateRenderer(template, variables)
        qti_rendered = tpl_renderer.render()
        return qti_rendered

    def to_html(self, interaction=None):
        template = 'element.html'
        variables = self.get_template_qti_variables()
        if 'attributes' in variables:
            variables['attributes'] = self.xmlize_options(variables['attributes'], True)
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered

    @staticmethod
    def render_item_html_template(template, variables):
        tpl_renderer = ItemRenderer(template, variables)
        html_rendered = tpl_renderer.render()
        return html_rendered

    def to_dict(self, filter_variable_content=False, filtered=None):
        import os

        data = {'serial': self.get_serial()}
        tag = self.get_qti_tag()
        if tag != '':
            data['qtiClass'] = tag
        data['attributes'] = self.get_attribute_values()

        if isinstance(self, FlowContainerMixin):
            data['body'] = self.get_body().to_dict(filter_variable_content, filtered)

        if os.environ.get("DEBUG", 'false') == 'true':
            data['debug'] = {
                'relatedItem': self.get_related_item().get_serial() if self.get_related_item() is not None else ''
            }
        return data

    def set_related_item(self, item, force=False):
        if self.relatedItem is not None and self.relatedItem.get_serial() == item.get_serial():
            pass
        elif force is False and self.relatedItem is not None:
            raise ValueError("Related item is set already.")
        else:
            for key, value in vars(self).items():
                if type(value) is dict:
                    for _, sub in value.items():
                        if isinstance(sub, Element):
                            sub.set_related_item(item)
                        elif isinstance(sub, ResponseIdentifier):
                            base_type = sub.get_value(True)
                            if base_type is not None:
                                base_type.get_referenced_object().set_related_item(item)
                elif isinstance(value, Element):
                    value.set_related_item(item)

            self.relatedItem = item

    def get_identified_element(self, identifier, element_classes=None):
        element = None
        if element_classes is None:
            element_classes = []

        related_item = self.get_related_item()
        if related_item is not None:
            collection = related_item.get_identified_elements()
            if len(element_classes) == 0:
                collection.get_unique(identifier)
            else:
                for cls in element_classes:
                    element = collection.get_unique(identifier, cls)
                    if element is not None:
                        break
        return element

    def get_related_item(self):
        return self.relatedItem

    def xmlize_options(self, formal_opts, recursive=False):
        import numbers

        xmlized = ''

        options = formal_opts if recursive else self.get_attribute_values()
        for key, value in options.items():
            if type(value) is str:
                v = html.escape(value, True)
                xmlized += ' ' + key + '="' + v + '"'
            elif isinstance(value, numbers.Number):
                xmlized += ' ' + key + '="' + str(value) + '"'
            elif type(value) is bool:
                v = 'true' if value else 'false'
                xmlized += ' ' + key + '="' + v + '"'
            elif type(value) is list:
                v = ' '.join(value)
                xmlized += ' ' + key + '="' + v + '"'
            elif type(value) is dict:
                xmlized += self.xmlize_options(value, True)

        return xmlized

    def get_composing_elements(self, class_name=''):
        return []

    def get_serial(self):
        if self.serial == '':
            self.serial = self.build_serial()
        return self.serial

    def build_serial(self):
        import os
        import random
        import string
        if os.environ.get("DEBUG", 'false') == 'true':
            prefix = type(self).__name__.lower() + '_'
        else:
            prefix = 'i'
        serial = prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        return serial

    def get_dict_serialized_element_collection(self, elements, filter_variable_content=False, filtered=None):
        if filtered is None:
            filtered = []
        data = {}
        for ele in elements.values():
            data[ele.get_serial()] = ele.to_dict(filter_variable_content, filtered)
        return data

    def get_dict_serialized_primitive_collection(self, elements):
        data = {}
        for key, value in elements.items():
            if type(value) is dict:
                data[key] = self.get_dict_serialized_primitive_collection(value)
            else:
                data[key] = value
        return data


