from lxml import etree

from .responseprocessing import ResponseProcessing
from .rule import RuleMixin
from .template import Template
from ..renderer.templaterendere import TemplateRenderer
from ..serializer.qtiserializer import QtiSerializer


class TemplatesDriven(RuleMixin, ResponseProcessing):
    def get_rule(self):
        raise ValueError("please use buildRule for templateDriven instead")

    @staticmethod
    def is_supported_template(uri):
        supported = [
            Template.MATCH_CORRECT, Template.MAP_RESPONSE, Template.MAP_RESPONSE_POINT,
            Template.NONE
        ]

        return uri in supported

    @staticmethod
    def create(item):
        template = TemplatesDriven()

        if len(item.get_outcomes()) == 0:
            item.set_outcomes({
                'identifier': 'SCORE',
                'baseType': 'float',
                'cardinality': 'single'
            })

        for interaction in item.get_interactions():
            template.set_template(interaction.get_response(), Template.MATCH_CORRECT)

        return template

    @staticmethod
    def take_over_from(response_processing, item):
        template = None

        if isinstance(response_processing, TemplatesDriven):
            return response_processing

        if isinstance(response_processing, Template):
            template = TemplatesDriven()
            for interaction in item.get_interactions().values():
                template.set_template(interaction.get_response(), response_processing.get_uri())
            template.set_related_item(item)
        return template

    def set_template(self, response, template):
        response.set_how_match(template)
        return True

    def get_template(self, response):
        return response.get_how_match()

    def take_notice_of_Added_interaction(self, interaction, item):
        interaction.get_response().set_how_match(Template.MATCH_CORRECT)

    def take_notice_of_removed_interaction(self, interaction, item):
        pass

    def build_qti(self):
        template = self.convert_to_template()
        if template is not None:
            return template.to_qti()

        value = "<responseProcessing>"
        interactions = self.get_related_item().get_interactions()
        for interaction in interactions.values():
            response = interaction.get_response()
            uri = response.get_how_match()
            matching_template = self.get_response_processing_template(uri)
            tpl_renderer = TemplateRenderer(matching_template,
                                            {'responseIdentifier': response.get_identifier(),
                                             'outcomeIdentifier': 'SCORE'})
            value += tpl_renderer.render()

            for rule in response.get_feedback_rules():
                value += rule.to_qti()

        value += "</responseProcessing>"

        return value

    def get_response_processing_template(self, template_uri):
        if template_uri == Template.NONE:
            matching_template = 'responses/qti_none.xml'
        else:
            template_name = template_uri.rsplit('/', 1)[1]
            matching_template = 'responses/qti_' + template_name + '.xml'
        return matching_template

    def to_qti(self):
        raise ValueError()

    def convert_to_template(self):
        template = None
        interactions = self.get_related_item().get_interactions()

        for interaction in interactions.values():
            if interaction.get_attribute_value('responseIdentifier') == 'RESPONSE':
                response = interaction.get_response()
                if len(response.get_feedback_rules()) == 0:
                    uri = response.get_how_match()
                    template = Template(uri)
            break

        return template

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        rp = None
        response_rules = []
        template = self.convert_to_template()

        if template is None:
            rp = self.build_qti()
        else:
            rp = template.get_template_content()

        if rp.strip() != '':
            rp_serialized = QtiSerializer.parse_response_processing_xml(etree.fromstring(rp))
            response_rules = rp_serialized['responseRules']

        protected_data = {
            'processingType': 'templateDriven',
            'responseRules': response_rules
        }

        if filter_variable_content:
            filtered[self.get_serial()] = protected_data
        else:
            data.update(protected_data)

        return data

    def get_used_attributes(self):
        return {}
