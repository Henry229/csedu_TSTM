from ..element import Element
from ..identifiedelementcontainer import IdentifiedElementContainerMixin
from ..identifiercollection import IdentifierCollection
from ..responsedeclaration import ResponseDeclaration


class Interaction(IdentifiedElementContainerMixin, Element):
    choiceClass = None
    baseType = ''

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.choices = {}

    def get_used_attributes(self):
        return [
            'ResponseIdentifier'
        ]

    def get_choices(self, set_number=None):
        return self.choices

    def get_choice_by_serial(self, serial):
        return self.choices.get(serial)

    def get_choice_by_identifier(self, identifier):
        return self.get_identified_elements().get_unique(identifier, 'Choice')

    def add_choice(self, choice, set_number=None):
        result = False
        self.choices[choice.get_serial()] = choice
        related_item = self.get_related_item()
        if related_item is not None:
            choice.set_related_item(related_item)
            result = True

        return result

    def create_choice(self, choice_attributes=None, choice_value=None, set_number=None):
        if choice_attributes is None:
            choice_attributes = {}
        choice = self.choiceClass(choice_attributes)
        choice.set_content(choice_value)
        self.add_choice(choice)

        return choice

    def remove_choice(self, choice, set_number=None):
        del self.choices[choice.get_serial()]

    def get_identified_elements(self):
        elements = IdentifierCollection()
        elements.add_multiple(self.get_choices())
        return elements

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        if 'identifier' in variables['attributes']:
            del variables['attributes']['identifier']
        variables['choices'] = ''
        for choice in self.get_choices().values():
            variables['choices'] = variables['choices'] + choice.to_qti()

        return variables

    def get_response(self):
        response = None
        response_attribute = self.get_attribute('responseIdentifier')
        if response_attribute is not None:
            identifier_base_type = response_attribute.get_value(True)
            if identifier_base_type is not None:
                response = identifier_base_type.get_referenced_object()
            else:
                response_declaration = ResponseDeclaration()
                if self.set_response(response_declaration):
                    response = response_declaration
                else:
                    raise ValueError()
        return response

    def set_response(self, response: ResponseDeclaration):
        related_item = self.get_related_item()
        if related_item is not None:
            related_item.add_response(response)
        return self.set_attribute('responseIdentifier', response)

    def get_cardinality(self, numeric=False):
        cardinality_value = None

        type_name = self.get_type()
        if type_name in ['choice', 'hottext', 'hotspot', 'selectpoint', 'positionobuect']:
            pass
        elif type_name in ['associate', 'match', 'graphicassociate']:
            pass
        elif type_name in ['extendedtext']:
            pass
        elif type_name in ['gapmatch']:
            pass
        elif type_name in ['graphicgapmatch']:
            pass
        elif type_name in ['order', 'graphicorder']:
            pass
        elif type_name in ['inlinechoice', 'textentry', 'slider', 'upload', 'endattempt']:
            pass
        else:
            raise ValueError()

        return cardinality_value

    def get_base_type(self):
        return self.baseType.lower()

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['choice'] = self.get_dict_serialized_element_collection(self.get_choices(), filter_variable_content,
                                                                     filtered)
        return data

    def can_render_testtaker_response(self):
        return self.get_type() in ['extentedtext']

    def get_type(self):
        tag_name = self.qtiTagName
        return tag_name.replace('Interaction', '')

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        response = self.get_response()
        variables['identifier'] = response.get_identifier()
        variables['baseType'] = response.get_base_type()
        return variables

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': to_html is not implemented')



