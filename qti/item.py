from jinja2 import Template

from .container.containeritembody import ContainerItemBody
from .container.flowcontainer import FlowContainerMixin
from .feedback.modalfeedback import ModalFeedback
from .identifiedelement import IdentifiedElement
from .identifiedelementcontainer import IdentifiedElementContainerMixin
from .itemrenderer.itemrenderer import ItemRenderer
from .outcomedeclaration import OutcomeDeclaration
from .renderer.templaterendere import TemplateRenderer
from .response.templatesdriven import TemplatesDriven
from .responsedeclaration import ResponseDeclaration
from .utils import ClassUtils


class Item(FlowContainerMixin, IdentifiedElementContainerMixin, IdentifiedElement):
    qtiTagName = 'assessmentItem'

    def __init__(self, attributes=None, related_item=None, serial=''):
        if attributes is None:
            attributes = {}
        self.resource_id = ''
        self.body = None
        self.responses = {}
        self.responseProcessing = None
        self.outcomes = {}
        self.stylesheets = {}
        self.modalFeedbacks = {}
        self.namespaces = {}
        self.schemaLocations = {}
        self.apipAccessibility = ''
        attributes['toolName'] = 'CSE'
        attributes['toolVersion'] = '1.0'
        self.body = ContainerItemBody('', self)
        super().__init__(attributes, related_item, serial)

    def get_resource_id(self):
        return self.resource_id

    def set_resource_id(self, resource_id):
        self.resource_id = resource_id

    def add_namespace(self, name, uri):
        self.namespaces[name] = uri

    def get_namespaces(self):
        return self.namespaces

    def get_namespace(self, uri):
        for name, value in self.namespaces.items():
            if value == uri:
                return name
        return None

    def set_apip_accessibility(self, apip_xml):
        self.apipAccessibility = apip_xml

    def get_apip_accessibility(self):
        return self.apipAccessibility

    def get_used_attributes(self):
        return [
            'Title', 'Label', 'Lang', 'Adaptive', 'TimeDependent', 'ToolName', 'ToolVersion'
        ]

    def get_body(self):
        return self.body

    def add_interaction(self, interaction, body):
        if interaction is not None:
            return self.body.set_element(interaction, body)
        return False

    def remove_interaction(self, interaction):
        if interaction is not None:
            return self.body.remove_element(interaction)
        return False

    def get_interactions(self):
        return self.body.get_elements('Interaction')

    def get_objects(self):
        return self.body.get_elements('Object')

    def get_rubric_block(self):
        return self.body.get_elements('RubricBlock')

    def get_related_item(self):
        return self

    def get_response_processing(self):
        return self.responseProcessing

    def set_response_processing(self, rprodcessing):
        self.responseProcessing = rprodcessing

    def add_schema_location(self, namespace, location):
        self.schemaLocations[namespace] = location

    def get_schema_locations(self):
        return self.schemaLocations

    def get_schema_location(self, uri):
        return self.schemaLocations.get(uri)

    def get_style_sheets(self):
        return self.stylesheets

    def add_stylesheet(self, stylesheet):
        self.stylesheets[stylesheet.get_serial()] = stylesheet
        stylesheet.set_related_item(self)

    def get_outcomes(self):
        return self.outcomes

    def set_outcomes(self, outcomes):
        self.outcomes = {}
        for outcome in outcomes:
            if not isinstance(outcome, OutcomeDeclaration):
                raise ValueError()
            self.add_outcome(outcome)

    def add_outcome(self, outcome: OutcomeDeclaration):
        self.outcomes[outcome.get_serial()] = outcome
        outcome.set_related_item(self)

    def add_response(self, response: ResponseDeclaration):
        self.responses[response.get_serial()] = response
        response.set_related_item(self)

    def get_responses(self):
        return self.responses

    def add_modal_feedback(self, feedback: ModalFeedback):
        self.modalFeedbacks[feedback.get_serial()] = feedback
        feedback.set_related_item(self)

    def remove_modal_feedback(self, feedback: ModalFeedback):
        del self.modalFeedbacks[feedback.get_serial()]

    def get_modal_feedbacks(self):
        return self.modalFeedbacks

    def get_modal_feedback(self, serial):
        return self.modalFeedbacks.get(serial, None)

    def get_identified_elements(self):
        elements = self.get_body().get_identified_elements()
        elements.add_multiple(self.get_outcomes())
        elements.add_multiple(self.get_responses())
        elements.add_multiple(self.get_modal_feedbacks())

        return elements

    @classmethod
    def get_template_qti(cls):
        # template_path = cls.get_template_path()
        tpl_name = 'qtiitem.xml'
        return tpl_name

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()

        variables['stylesheets'] = ''
        for stylesheet in self.stylesheets.values():
            variables['stylesheets'] += stylesheet.to_qti()

        variables['responses'] = ''
        for response in self.responses.values():
            variables['responses'] += response.to_qti()

        variables['outcomes'] = ''
        for outcome in self.outcomes.values():
            variables['outcomes'] += outcome.to_qti()

        variables['feedbacks'] = ''
        for feedback in self.modalFeedbacks:
            variables['feedbacks'] += feedback.to_qti()

        variables['namespaces'] = self.get_namespaces()
        schema_locations = ''
        for uri, url in self.get_schema_locations().items():
            schema_locations += uri + ' ' + url + ' '

        variables['schemaLocations'] = schema_locations.strip()
        ns_xsi = self.get_namespace('http://www.w3.org/2001/XMLSchema-instance')
        variables['xsi'] = ns_xsi + ':' if ns_xsi is not None else 'xsi:'

        rendered_response_processing = ''
        response_processing = self.get_response_processing()
        if response_processing is not None:
            if isinstance(response_processing, TemplatesDriven):
                rendered_response_processing = response_processing.build_qti()
            else:
                rendered_response_processing = response_processing.to_qti()

        variables['class'] = self.get_attribute_value('class')
        del variables['attributes']['class']

        variables['renderedResponseProcessing'] = rendered_response_processing

        variables['apipAccessibility'] = self.get_apip_accessibility()

        return variables

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['namespaces'] = self.get_namespaces()
        data['schemaLocations'] = self.get_schema_locations()
        data['stylesheets'] \
            = self.get_dict_serialized_element_collection(self.get_style_sheets(), filter_variable_content, filtered)
        data['outcomes'] \
            = self.get_dict_serialized_element_collection(self.get_outcomes(), filter_variable_content, filtered)
        data['responses'] \
            = self.get_dict_serialized_element_collection(self.get_responses(), filter_variable_content, filtered)
        data['feedbacks'] \
            = self.get_dict_serialized_element_collection(self.get_modal_feedbacks(), filter_variable_content, filtered)
        data['responseProcessing'] = self.responseProcessing.to_dict(filter_variable_content, filtered)
        data['apipAccessibility'] = self.get_apip_accessibility()
        return data

    def to_xhtml(self, options=None, filtered=None):
        import json

        if options is None:
            options = {}
        if filtered is None:
            filtered = {}
        template = 'qtiitem.html'

        variables = self.get_attribute_values()
        variables['stylesheets'] = []
        for stylesheet in self.get_style_sheets():
            variables['stylesheets'].append(stylesheet.get_attribute_values())

        if 'css' in options:
            for css in options['css']:
                variables['stylesheets'].append({'href': css, 'media': 'all'})

        variables['javascripts'] = []
        variables['js_variables'] = {}
        if 'js' in options:
            for js in options['js']:
                variables['javascripts'].append({'src': js})
        if 'js_var' in options:
            for name, value in options['js_var'].items():
                variables['js_variables'][name] = value

        data_for_delivery = self.get_data_for_delivery()
        variables['itemData'] = json.dumps(data_for_delivery['core'])
        for serial, data in data_for_delivery['variable'].items():
            filtered[serial] = data

        tpl_renderer = TemplateRenderer(template, variables)
        html_rendered = tpl_renderer.render()

        return html_rendered

    def to_html(self, interaction=None):
        template = 'item.html'
        variables = {
            'serial': self.get_serial(),
            'attributes': self.get_attribute_values(),
        }
        body = self.get_body()
        body_tpl = Template(body.get_body())
        body_variables = {}
        for name, element in body.get_elements().items():
            body_variables[name] = element.to_html()

        variables['body'] = body_tpl.render(body_variables)
        tpl_renderer = ItemRenderer(template, variables)
        html_rendered = tpl_renderer.render()

        return html_rendered

    def get_interaction_object_variables(self):
        interactions = self.get_interactions()
        variables = {}
        for key, itr in interactions.items():
            if ClassUtils.is_subclass_by_name(itr, 'ObjectInteraction'):
                variables[key] = itr.get_object_variables()
        return variables

    def get_data_for_delivery(self):
        filtered = {}
        item_data = self.to_dict(True, filtered)
        del item_data['responseProcessing']

        return {'core': item_data, 'variable': filtered}

    # ---------------------
    # Helper functions.
    # ---------------------
    def get_interaction_info(self):
        interactions = []
        for element in self.body.get_elements().values():
            if ClassUtils.is_subclass_by_name(element, 'Interaction'):
                inter = {
                    'type':  element.get_qti_tag(),
                    'attributes': element.get_attribute_values()
                }
                interactions.append(inter)
        return interactions

    def get_interaction_type(self):
        # ToDo: 여러개의 interaction type 을 보여야함.
        from .utils import ClassUtils
        interaction_type = ''
        for element in self.body.get_elements().values():
            if ClassUtils.is_subclass_by_name(element, 'Interaction'):
                interaction_type = element.get_qti_tag()
        return interaction_type

    def get_cardinality(self):
        for response in self.get_responses().values():
            return response.get_attribute_value('cardinality')
        return None

    def get_base_type(self):
        for response in self.get_responses().values():
            return response.get_attribute_value('baseType')
        return None

    def get_correct_response(self):
        correct_responses = []
        for response in self.get_responses().values():
            for rsp in response.correctResponses:
                correct_responses.append(rsp.get_value())
        return ','.join(correct_responses)

