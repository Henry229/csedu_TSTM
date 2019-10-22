from .contentvariable import ContentVariableMixin
from .response.template import Template
from .variabledeclaration import VariableDeclaration


class ResponseDeclaration(ContentVariableMixin, VariableDeclaration):
    """
    Response variables are declared by response declarations and bound to interactions in the itemBody.
    Each response variable declared may be bound to one and only one interaction.

        - reference: https://www.imsglobal.org/question/qtiv2p1/imsqti_infov2p1.html#element10073
    """

    qtiTagName = 'responseDeclaration'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.correctResponses = {}
        self.mapping = {}
        self.areaMapping = {}
        self.mappingDefaultValue = 0.0
        self.howMatch = None
        self.simpleFeedbackRules = {}

    def get_correct_responses(self):
        return self.correctResponses

    def set_correct_responses(self, responses):
        self.correctResponses = responses

    def get_mapping(self, type=''):
        if type == 'area':
            return self.areaMapping
        else:
            return self.mapping

    def set_mapping(self, map, type=''):
        if type == 'area':
            self.areaMapping = map
        else:
            self.mapping = map

    def get_mapping_default_value(self):
        return self.mappingDefaultValue

    def set_mapping_default_value(self, value):
        self.mappingDefaultValue = value

    def get_base_type(self):
        return self.get_attribute_value('baseType')

    def get_how_match(self):
        return self.howMatch

    def set_how_match(self, how_match):
        self.howMatch = how_match

    def get_feedback_rules(self):
        return self.simpleFeedbackRules

    def get_feedback_rule(self, serial):
        return self.simpleFeedbackRules.get(serial)

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        if 'mapping' in data['attributes']:
            del data['attributes']['mapping']
        if 'areaMapping' in data['attributes']:
            del data['attributes']['areaMapping']

        protected_data = {
            'mapping': self.mapping,
            'areaMapping': self.areaMapping,
            'howMatch': self.howMatch
        }

        correct = {}
        correct_responses = self.get_correct_responses()
        if type(correct_responses) is dict:
            for key, value in correct_responses.items():
                if self.get_attribute('cardinality') == 'record':
                    value_data = value.to_dict()
                    correct[value_data['fieldIdentifier']] = value_data
                else:
                    correct[key] = value

        protected_data['correctResponse'] = correct

        default_values = self.get_default_value()
        if type(default_values) is dict:
            for key, value in default_values:
                default_values[key] = value
        protected_data['defaultValue'] = default_values
        data['defaultValue'] = default_values

        mapping_attributes = {
            'defaultValue': self.mappingDefaultValue,
        }
        if type(self.get_attribute_value('mapping')) is dict:
            mapping_attributes.update(self.get_attribute_value('mapping'))
        elif type(self.get_attribute_value('areaMapping')) is dict:
            mapping_attributes.update(self.get_attribute_value('areaMapping'))
        protected_data['mappingAttributes'] = mapping_attributes

        protected_data['feedbackRules'] = self.get_dict_serialized_element_collection(self.get_feedback_rules(),
                                                                                      filter_variable_content, filtered)

        if filter_variable_content:
            filtered[self.get_serial()] = protected_data
        else:
            data.update(protected_data)

        return data

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['correctResponses'] = self.get_correct_responses()
        variables['defaultValue'] = self.get_default_value()

        variables['mapping'] = self.mapping
        variables['areaMapping'] = self.areaMapping

        if variables['attributes'].get('mapping'):
            del variables['attributes']['mapping']
        if variables['attributes'].get('areaMapping'):
            del variables['attributes']['areaMapping']

        mapping_attributes = {
            'defaultValue': self.mappingDefaultValue,
        }
        if type(self.get_attribute_value('mapping')) is dict:
            mapping_attributes.update(self.get_attribute_value('mapping'))
        elif type(self.get_attribute_value('areaMapping')) is dict:
            mapping_attributes.update(self.get_attribute_value('areaMapping'))

        variables['mappingAttributes'] = self.xmlize_options(mapping_attributes, True)

        rp_template = ''
        if self.howMatch is Template.MATCH_CORRECT:
            rp_template = 'match_correct'
        elif self.howMatch is Template.MAP_RESPONSE:
            rp_template = 'map_response'
        elif self.howMatch is Template.MAP_RESPONSE_POINT:
            rp_template = 'map_response_point'

        variables['howMatch'] = self.howMatch
        variables['rpTemplate'] = rp_template

        return variables


