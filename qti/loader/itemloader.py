import re

from lxml import etree

from ..container.containerinteractive import ContainerInteractive
from ..container.containeritembody import ContainerItemBody
from ..exceptions import QtiLoaderError
from ..feedback import is_valid_feedback_class, create_feedback_class_object
from ..feedback.modalfeedback import ModalFeedback
from ..img import Img
from ..interaction import create_interaction_class_object, is_valid_interaction_class
from ..interaction.blockinteraction import BlockInteraction
from ..item import Item
from ..math import Math
from ..objectelement import Object
from ..outcomedeclaration import OutcomeDeclaration
from ..response.custom import Custom
from ..response.simplefeedbackrule import SimpleFeedbackRule
from ..response.template import Template
from ..response.templatesdriven import TemplatesDriven
from ..responsedeclaration import ResponseDeclaration
from ..rubricblock import RubricBlock
from ..stylesheet import Stylesheet
from ..table import Table
from ..value import Value
from ..xinclude import XInclude

XSI = "http://www.w3.org/2001/XMLSchema-instance"


class ItemLoader:

    def __init__(self, file_path):
        self.etree = etree.parse(file_path)
        self.item = None
        self.root = self.etree.getroot()
        self.namespace = self.root.nsmap.get(None)
        # objectify.deannotate(self.root, cleanup_namespaces=True)

    def build_item(self):
        self.item = Item(self.extract_attributes(self.root))

        self.load_namespaces()
        self.load_schema_locations()

        # load stylesheets
        stylesheet_nodes = self.query_xpath("*[name(.) = 'stylesheet']", self.root)

        for node in stylesheet_nodes:
            stylesheet = self.build_stylesheet(node)
            self.item.add_stylesheet(stylesheet)

        # extract the responses
        response_nodes = self.query_xpath("*[name(.) = 'responseDeclaration']", self.root)
        for node in response_nodes:
            response = self.build_response_declaration(node)
            if response is not None:
                self.item.add_response(response)

        # extract outcome variables
        outcomes = []
        outcome_nodes = self.query_xpath("*[name(.) = 'outcomeDeclaration']", self.root)
        for node in outcome_nodes:
            outcome = self.build_outcome_declaration(node)
            if outcome is not None:
                outcomes.append(outcome)
        if len(outcomes) > 0:
            self.item.set_outcomes(outcomes)

        # extract modal feedbacks
        feedback_nodes = self.query_xpath("*[name(.) = 'modalFeedback']", self.root)
        for node in feedback_nodes:
            modal_feedback = self.build_feedback(node)
            if modal_feedback is not None:
                self.item.add_modal_feedback(modal_feedback)

        # extract the item structure to separate the structural / style content to the item content
        item_bodies = self.query_xpath("*[name(.) = 'itemBody']", self.root)  # array with 1 or zero bodies
        if item_bodies is None:
            raise ValueError()
        elif len(item_bodies):
            self.parse_container_item_body(item_bodies[0], self.item.get_body())
            self.item.add_class(item_bodies[0].get('class', ''))

        # warning: extract the response processing at the latest to make
        # response.TemplatesDriven.takeOverFrom() work
        rp_nodes = self.query_xpath("*[name(.) = 'responseProcessing']", self.root)
        if len(rp_nodes) == 0:
            # no response processing node found: the template for an empty response processing is simply "NONE"
            r_processing = TemplatesDriven()
            r_processing.set_related_item(self.item)
            for interaction in self.item.get_interactions():
                r_processing.set_template(interaction.getresponse(), Template.NONE)
            self.item.set_response_processing(r_processing)
        else:
            # if there is a response processing node, try parsing it
            rp_node = rp_nodes[0]
            r_processing = self.build_response_processing(rp_node, self.item)
            if r_processing is not None:
                self.item.set_response_processing(r_processing)
        self.build_apip_accessibility(self.root)
        return self.item

    @staticmethod
    def extract_attributes(element):
        attributes = {}
        attrib = element.attrib
        for name, value in attrib.items():
            # remove namespace from the attribute name which is format of {http://xxxxx} .
            name = re.sub(r'{.+?}', '', name)
            if not name.endswith('schemaLocation'):
                attributes[name] = value
        return attributes

    def find_namespace(self, ns_fragment):
        name_space = ''
        if self.item is None:
            for node in self.query_xpath('namespace::*'):
                name = node.nodeName.replace('/xmlns(:)?/', '')
                urk = node.value
        # ToDo : not implemented

        return name_space

    def find(self, tag_name, context_node=None):
        if context_node is None:
            return self.root.find('{' + self.namespace + '}' + tag_name)
        else:
            return context_node.find('{' + self.namespace + '}' + tag_name)

    def findall(self, tag_name, context_node=None):
        if context_node is None:
            return self.root.findall('{' + self.namespace + '}' + tag_name)
        else:
            return context_node.findall('{' + self.namespace + '}' + tag_name)

    def simple_tag(self, node):
        return node.tag.replace('{' + self.namespace + '}', '')

    def tag_class_name(self, node):
        tag_name = self.simple_tag(node)
        return tag_name[:1].upper() + tag_name[1:]

    def get_math_namespace(self):
        return self.find_namespace('MathML')

    def get_xinclude_namespace(self):
        return self.find_namespace('XInclude')

    def load_namespaces(self):
        for node in self.query_xpath('namespace::*'):
            if node[0] != 'xml':
                self.item.add_namespace(node[0], node[1])

    def load_schema_locations(self):
        schema_locations = set(self.etree.xpath("//*/@xsi:schemaLocation", namespaces={'xsi': XSI}))
        for schema_location in schema_locations:
            # Split namespaces and schema locations ; use strip to remove leading
            # and trailing whitespace.
            namespaces_locations = schema_location.strip().split()
            # Import all found namspace/schema location pairs
            for namespace, location in zip(*[iter(namespaces_locations)] * 2):
                self.item.add_schema_location(namespace, location)

    def query_xpath(self, query, context_node=None):
        if context_node is None:
            return self.etree.xpath(query)
        else:
            return context_node.xpath(query)

    def query_xpath_children(self, paths=None, context_node=None, ns=''):
        if paths is None:
            paths = []
        query = '.'
        ns = '' if ns == '' else ns + ':'
        for path in paths:
            query += "/*[name(.)='" + ns + path + "']"
        return self.query_xpath(query, context_node)

    def get_body_data(self, data, remove_namespace=False, keep_empty_tags=False):
        children_data = []
        for child in data:
            localname = etree.QName(child).localname
            child.tag = localname
            child_str = etree.tostring(child, encoding='unicode')
            children_data.append(re.sub(r'\s*xmlns[:]*\w*=\".+?\"', "", child_str, flags=re.IGNORECASE))
        if data.text is None:
            body_data = ''
        else:
            body_data = data.text
        body_data += ''.join(children_data)
        return body_data

    @staticmethod
    def replace_node(node, element):
        """
        https://stackoverflow.com/a/10520552/1371741
        :param node:
        :param element:
        :return:
        """
        place_holder = element.get_placeholder()
        node_text = place_holder + node.tail if node.tail else place_holder
        parent = node.getparent()
        if parent is not None:
            previous = node.getprevious()
            if previous is not None:
                previous.tail = (previous.tail or '') + node_text
            else:
                parent.text = (parent.text or '') + node_text
            parent.remove(node)

    def delete_node(self, node):
        node.getparent().remove(node)

    def build_stylesheet(self, data):
        attributes = {
            'href': data.get('href'),
            'title': data.get('title', ''),
            'media': data.get('media', 'screen'),
            'type': data.get('type', 'text/css')
        }
        stylesheet = Stylesheet(attributes)
        return stylesheet

    def build_feedback(self, data) -> ModalFeedback:
        cls_name = data.nodeName

        if is_valid_feedback_class(cls_name):
            raise ValueError()

        attributes = self.extract_attributes()
        feedback = None
        if data.nodeName == 'modalFeedback':
            feedback = create_feedback_class_object(cls_name, attributes, self.item)
            self.parse_container_static(data, feedback.get_body())
        return feedback

    def build_object(self, data):
        attributes = self.extract_attributes(data)
        obj = Object(attributes)
        # ToDo: not implemented
        return obj

    def build_img(self, data):
        attributes = self.extract_attributes(data)
        img = Img(attributes)

        return img

    def build_table(self, data):
        attributes = self.extract_attributes(data)
        table = Table(attributes)
        self.parse_container_static(data, table.get_body())
        return table

    def build_math(self, data):
        ns = self.get_math_namespace()
        ns = ns + ':' if ns else ''
        annotation_nodes = self.query_xpath(".//*[name(.)='" + ns + "annotation']", data)
        annotations = {}
        for node in annotation_nodes:
            attr = self.extract_attributes(node)
            encoding = attr.get('encoding', '')
            str_value = self.get_body_data(node)
            if str_value != '' and encoding != '':
                annotations[encoding] = str_value
                self.delete_node(node)

        math = Math(self.extract_attributes(data))
        body = self.get_body_data(data, True)
        math.set_mathml(body)
        math.set_annotations(annotations)

        return math

    def build_xinclude(self, data):
        return XInclude(self.extract_attributes())

    def build_rubric_block(self, data):
        block = RubricBlock(self.extract_attributes())
        self.parse_container_static(data, block.get_body())

        return block

    def get_pci_namespace(self):
        return 'pci'

    def is_pci_node(self, data):
        ns = self.get_pci_namespace()
        children = self.query_xpath_children(['portableInfoControl'], data, ns)
        return len(children) > 0

    def build_info_control(self, data):
        info_control = None
        if self.is_pci_node(data):
            # ToDo : not implemented
            pass
        else:
            # ToDo : not implemented
            pass
        return info_control

    def build_choice(self, data):
        from ..choice import create_choice_class_object, is_valid_choice_class
        from ..choice import ContainerChoice, TextVariableChoice, GapImg

        cls_name = self.tag_class_name(data)
        if not is_valid_choice_class(cls_name):
            raise ValueError("Choice class is not valid.")

        choice = create_choice_class_object(cls_name, self.extract_attributes(data))
        if isinstance(choice, ContainerChoice):
            self.parse_container_static(data, choice.get_body())
        elif isinstance(choice, TextVariableChoice):
            choice.set_content(self.get_body_data(data))
        elif isinstance(choice, GapImg):
            object_nodes = self.query_xpath("*[name(.)='object']", data)
            for node in object_nodes:
                obj = self.build_object(node)
                choice.set_content(obj)
                break
        return choice

    def build_response_declaration(self, data):
        response_declaration = ResponseDeclaration(self.extract_attributes(data), self.item)
        correct_response_nodes = data.xpath("*[name(.) = 'correctResponse']")
        responses = []
        for node in correct_response_nodes:
            for value in self.findall('value', node):
                correct = value.text
                response = Value()
                attributes = value.attrib
                for attr_name, attr_value in attributes.items():
                    response.set_attribute(attr_name, attr_value)
                response.set_value(correct)
                responses.append(response)
            break

        response_declaration.set_correct_responses(responses)

        default_value_nodes = data.xpath("*[name(.) = 'defaultValue']")
        default_values = []
        for node in default_value_nodes:
            for value in self.findall('value', node):
                default = value.text
                default_value = Value()
                attributes = value.attrib
                for attr_name, attr_value in attributes.items():
                    default_value.set_attribute(attr_name, attr_value)
                default_value.set_value(default)
                default_values.append(default_value)
            break
        response_declaration.set_default_value(default_values)

        mapping_nodes = data.xpath("*[name(.) = 'mapping']")
        for node in mapping_nodes:
            if node.get('defaultValue') is not None:
                response_declaration.set_mapping_default_value(float(node.get('defaultValue')))
            mapping_options = {}
            attributes = node.attrib
            for attr_name, attr_value in attributes.items():
                if attr_name != 'defaultValue':
                    mapping_options[attr_name] = attr_value
            response_declaration.set_attribute('mapping', mapping_options)

            mapping = {}
            for entry in self.findall('mapEntry', node):
                mapping[entry.get('mapKey')] = entry.get('mappedValue')
            response_declaration.set_mapping(mapping)

            break

        mapping_nodes = data.xpath("*[name(.) = 'areaMapping']")
        for node in mapping_nodes:
            if node.get('defaultValue') is not None:
                response_declaration.set_mapping_default_value(float(node.get('defaultValue')))
            mapping_options = {}
            attributes = node.attrib
            for attr_name, attr_value in attributes.items():
                if attr_name != 'defaultValue':
                    mapping_options[attr_name] = attr_value
            response_declaration.set_attribute('areaMapping', mapping_options)

            mapping = []
            for entry in node.inter('areaMapEntry'):
                mapping_attributes = {}
                for attr_name, attr_value in entry.items():
                    mapping_attributes[attr_name] = attr_value
                mapping.append(mapping_attributes)
            response_declaration.set_mapping(mapping, 'area')

            break

        return response_declaration

    def build_outcome_declaration(self, data):
        outcome = OutcomeDeclaration(self.extract_attributes(data))

        default_value = self.find('defaultValue', data)
        if default_value is not None:
            value = self.find('value', default_value)
            if value is not None:
                outcome.set_default_value(value.text)
        return outcome

    def build_template_response_processing(self, data):
        template = None
        children = data.getchildren()
        if data.get('template') is not None and len(children) == 0:
            template_uri = data.get('template')
            template = Template(template_uri)
        elif len(children) == 1:
            responses = self.item.get_responses()
            if len(responses) == 1:
                response = responses[0]
                if response.get_identifier() != 'RESPONSE':
                    raise ValueError()
            else:
                raise ValueError()

            pattern_correct = 'responseCondition [count(./*) = 2 ] [name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "match" ] [name(./responseIf/match/*[1]) = "variable" ] [name(./responseIf/match/*[2]) = "correct" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ] [name(./*[2]) = "responseElse" ] [count(./responseElse/*) = 1 ] [name(./responseElse/*[1]) = "setOutcomeValue" ] [name(./responseElse/setOutcomeValue/*[1]) = "baseValue"]';
            pattern_mapping = 'responseCondition [count(./*) = 2] [name(./*[1]) = "responseIf"] [count(./responseIf/*) = 2] [name(./responseIf/*[1]) = "isNull"] [name(./responseIf/isNull/*[1]) = "variable"] [name(./responseIf/*[2]) = "setOutcomeValue"] [name(./responseIf/setOutcomeValue/*[1]) = "variable"] [name(./*[2]) = "responseElse"] [count(./responseElse/*) = 1] [name(./responseElse/*[1]) = "setOutcomeValue"] [name(./responseElse/setOutcomeValue/*[1]) = "mapResponse"]';
            pattern_mapping_point = 'responseCondition [count(./*) = 2] [name(./*[1]) = "responseIf"] [count(./responseIf/*) = 2] [name(./responseIf/*[1]) = "isNull"] [name(./responseIf/isNull/*[1]) = "variable"] [name(./responseIf/*[2]) = "setOutcomeValue"] [name(./responseIf/setOutcomeValue/*[1]) = "variable"] [name(./*[2]) = "responseElse"] [count(./responseElse/*) = 1] [name(./responseElse/*[1]) = "setOutcomeValue"] [name(./responseElse/setOutcomeValue/*[1]) = "mapResponsePoint"]';
            if len(self.query_xpath(pattern_correct)) == 1:
                template = Template(Template.MATCH_CORRECT)
            elif len(self.query_xpath(pattern_mapping)) == 1:
                template = Template(Template.MAP_RESPONSE)
            elif len(self.query_xpath(pattern_mapping_point)) == 1:
                template = Template(Template.MAP_RESPONSE_POINT)
            else:
                raise ValueError()
            template.set_related_item(self.item)
        else:
            raise ValueError()

        return template

    def build_response_processing(self, data, item: Item):
        response_processing = None
        try:
            response_processing = self.build_template_response_processing(data)
            try:
                response_processing = TemplatesDriven.take_over_from(response_processing, item)
            except ValueError:
                pass
        except ValueError:
            pass

        if response_processing is None:
            try:
                response_processing = self.build_template_driven_response(data, item.get_interactions())
            except ValueError:
                pass
        if response_processing is None:
            try:
                response_processing = self.build_custom_response_processing(data)
            except ValueError:
                pass
        return response_processing

    def build_apip_accessibility(self, data):
        apip_nodes = self.query_xpath("*[name(.) = 'apipAccessibility']|*[name(.) = 'apip:apipAccessibility']", data)
        if len(apip_nodes) > 0:
            apip_node = apip_nodes.item(0)
            apip_xml = apip_node.ownerDocument.saveXML(apip_node)
            self.item.set_apip_accessibility(apip_xml)

    def build_interaction(self, data):
        from ..interaction import ObjectInteraction

        interaction = None
        tag_name = self.simple_tag(data)
        if tag_name == 'customInteraction':
            # interaction = self.build_custom_interaction(data)
            raise NotImplementedError('customInteraction is not implemented.')
        else:
            cls_name = self.tag_class_name(data)
            if not is_valid_interaction_class(cls_name):
                raise QtiLoaderError(cls_name + ' is not a valid interaction class.')

            interaction = create_interaction_class_object(cls_name, self.extract_attributes(data), self.item)
            if isinstance(interaction, BlockInteraction):
                prompt_nodes = self.query_xpath("*[name(.) = 'prompt']", data)
                for node in prompt_nodes:
                    self.parse_container_static(node, interaction.get_prompt())
                    self.delete_node(node)
            lower_name = cls_name.lower()
            if lower_name == 'matchinteraction':
                match_set_nodes = self.query_xpath("*[name(.) = 'simpleMatchSet']", data)
                match_set_number = 0
                for node in match_set_nodes:
                    choice_nodes = self.query_xpath("*[name(.) = 'simpleAssociableChoice']", node)
                    for choice_node in choice_nodes:
                        choice = self.build_choice(choice_node)
                        if choice is not None:
                            interaction.add_choice(choice, match_set_number)
                    match_set_number += 1
                    if match_set_number == 2:
                        break
            elif lower_name == 'gapmatchinteraction':
                choice_nodes = self.query_xpath("*[name(.)='gapText']", data)
                for node in choice_nodes:
                    choice = self.build_choice(node)
                    if choice is not None:
                        interaction.add_choice(choice)
                        self.delete_node(node)
                self.parse_container_gap(data, interaction.get_body())
            elif lower_name == 'hottextinteraction':
                self.parse_container_hottext(data, interaction.get_body())
            elif lower_name == 'graphicgapmatchinteraction':
                choice_nodes = self.query_xpath("*[name(.)='gapImg']", data)
                for node in choice_nodes:
                    choice = self.build_choice(node)
                    if choice is not None:
                        interaction.add_gap_img(choice)
                exp = "*[contains(name(.),'Choice')] | *[name(.)='associableHotspot']"
                choice_nodes = self.query_xpath(exp, data)
                for node in choice_nodes:
                    choice = self.build_choice(node)
                    if choice is not None:
                        interaction.add_choice(choice)
            else:
                exp = "*[contains(name(.),'Choice')] | *[name(.)='associableHotspot']"
                choice_nodes = self.query_xpath(exp, data)
                for node in choice_nodes:
                    choice = self.build_choice(node)
                    if choice is not None:
                        interaction.add_choice(choice)

            if isinstance(interaction, ObjectInteraction):
                object_nodes = self.query_xpath("*[name(.)='object']", data)
                for node in object_nodes:
                    obj = self.build_object(node)
                    if obj is not None:
                        interaction.set_object(obj)

        return interaction

    def build_custom_interaction(self, data):
        interaction = None

        return interaction

    def parse_container_static(self, data, container):
        body_elements = {}

        feedback_nodes = self.query_xpath(".//*[not(ancestor::feedbackBlock) and not(ancestor::feedbackInline) and contains(name(.), 'feedback')]", data)
        for node in feedback_nodes:
            feedback = self.build_feedback(node)
            if feedback is not None:
                body_elements[feedback.get_serial()] = feedback
                self.replace_node(node, feedback)

        table_nodes = self.query_xpath(".//*[name(.)='table']", data)
        for node in table_nodes:
            table = self.build_table(node)
            if table is not None:
                body_elements[table.feedback.get_serial()] = table
                self.replace_node(node, table)

        object_nodes = self.query_xpath(".//*[name(.)='object']", data)
        for node in object_nodes:
            if 'object' in self.get_ancestors(node):
                obj = self.build_object(node)
                if obj is not None:
                    body_elements[obj.get_serial()] = obj
                    self.replace_node(node, obj)

        img_nodes = self.query_xpath(".//*[name(.)='img']", data)
        for node in img_nodes:
            img = self.build_img(node)
            if img is not None:
                body_elements[img.get_serial()] = img
                self.replace_node(node, img)

        ns = self.get_math_namespace()
        ns = ns + ':' if ns else ''
        math_nodes = self.query_xpath(".//*[name(.)='" + ns + "math']", data)
        for node in math_nodes:
            math = self.build_math(node)
            if math is not None:
                body_elements[math.get_serial()] = math
                self.replace_node(node, math)

        ns = self.get_xinclude_namespace()
        ns = ns + ':' if ns else ''
        xinclude_nodes = self.query_xpath(".//*[name(.)='" + ns + "include']", data)
        for node in xinclude_nodes:
            include = self.build_xinclude(node)
            if include is not None:
                body_elements[include.get_serial()] = node
                self.replace_node(node, include)

        printed_variable_node = self.query_xpath(".//*[name(.)='printedVariable']", data)
        for node in printed_variable_node:
            raise ValueError()

        template_nodes = self.query_xpath(".//*[name(.)='templateBlock'] | *[name(.)='templateInline']", data)
        for node in template_nodes:
            raise ValueError()

        body_data = self.get_body_data(data)

        if not body_elements:
            container.edit(body_data)
        elif not container.set_elements(body_elements, body_data):
            raise ValueError()

        return data

    def parse_container_interactive(self, data, container:ContainerInteractive):
        body_elements = {}
        interaction_nodes = self.query_xpath(".//*[not(ancestor::feedbackBlock) and not(ancestor::feedbackInline) and contains(name(.), 'Interaction')]", data)
        for node in interaction_nodes:
            if 'portableCustomInteraction' not in node.tag:
                interaction = self.build_interaction(node)
                if interaction is not None:
                    body_elements[interaction.get_serial()] = interaction
                    self.replace_node(node, interaction)

        feedback_nodes = self.query_xpath(".//*[not(ancestor::feedbackBlock) and not(ancestor::feedbackInline) and contains(name(.), 'feedback')]", data)
        for node in feedback_nodes:
            feedback = self.build_feedback(node)
            if feedback is not None:
                body_elements[feedback.get_serial()] = feedback
                self.replace_node(node, feedback)

        body_data = self.get_body_data(data)
        serials_to_remove = []
        for element in body_elements.values():
            if element.get_placeholder() not in body_data:
                serials_to_remove.append(element.get_serial())
        for serial in serials_to_remove:
            del body_elements[serial]

        if not container.set_elements(body_elements, body_data):
            raise ValueError()

        return self.parse_container_static(data, container)

    def parse_container_item_body(self, data, container: ContainerItemBody):
        body_elements = {}
        rubric_nodes = self.query_xpath(".//*[name(.)='rubricBlock']", data)
        for node in rubric_nodes:
            block = self.build_rubric_block(node)
            if block is not None:
                body_elements[block.get_serial()] = block
                self.replace_node(node, block)

        info_control_nodes = self.query_xpath(".//*[name(.)='infoControl']", data)
        for node in info_control_nodes:
            control = self.build_info_control(node)
            if control is not None:
                body_elements[control.get_serial()] = control
                self.replace_node(node, control)

        table_nodes = self.query_xpath(".//*[name(.)='table']", data)
        for node in table_nodes:
            interaction_nodes = self.query_xpath(".//*[contains(name(.), 'Interaction')]", node)
            if len(interaction_nodes) > 0:
                table = self.build_table(node)
                if table is not None:
                    body_elements[table.get_serial()] = table
                    self.replace_node(node, table)
                    self.parse_container_interactive(node, table.get_body())

        self.set_container_elements(container, data, body_elements)

        return self.parse_container_interactive(data, container)

    def parse_container_choice(self, data, container, tag):
        choices = {}
        nodes = self.query_xpath(".//*[name(.)='" + tag + "']", data)
        for node in nodes:
            gap = self.build_choice(node)
            if gap is not None:
                choices[gap.get_serial()] = gap
                self.replace_node(node, gap)
        body_data = self.get_body_data(data)
        container.set_elements(choices, body_data)

        data = self.parse_container_static(data, container)
        return data

    def parse_container_gap(self, data, container):
        return self.parse_container_choice(data, container, 'gap')

    def parse_container_hottext(self, data, container):
        return self.parse_container_choice(data, container, 'hottext')

    def set_container_elements(self, container, data, body_elements=None):
        if body_elements is None:
            body_elements = {}

        body_data = self.get_body_data(data)
        for element in body_elements:
            if element.get_placeholder() not in body_data:
                del body_elements[element.get_serial()]

        if not container.set_elements(body_elements, body_data):
            raise ValueError()

    def get_ancestors(self, data, top_node='itemBody'):
        ancestors = []
        parent_node_name = ''
        current_node = data
        i = 0
        while current_node.parent() is not None and parent_node_name != top_node:
            if i > 100:
                raise ValueError()

            parent_node_name = current_node.parent().nodeName
            ancestors.append(current_node.parent())
            current_node = current_node.parent
            i += 1

        return ancestors

    def build_template_driven_response(self, data, interactions):
        pattern_correct = '/responseCondition [count(./*) = 1 ] [name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "match" ] [name(./responseIf/match/*[1]) = "variable" ] [name(./responseIf/match/*[2]) = "correct" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "sum" ] [name(./responseIf/setOutcomeValue/sum/*[1]) = "variable" ] [name(./responseIf/setOutcomeValue/sum/*[2]) = "baseValue"]'
        pattern_mapping = '/responseCondition [count(./*) = 1] [name(./*[1]) = "responseIf"] [count(./responseIf/*) = 2] [name(./responseIf/*[1]) = "not"] [name(./responseIf/not/*[1]) = "isNull"] [name(./responseIf/not/isNull/*[1]) = "variable"] [name(./responseIf/*[2]) = "setOutcomeValue"] [name(./responseIf/setOutcomeValue/*[1]) = "sum"] [name(./responseIf/setOutcomeValue/sum/*[1]) = "variable"] [name(./responseIf/setOutcomeValue/sum/*[2]) = "mapResponse"]'
        pattern_mapping_point = '/responseCondition [count(./*) = 1] [name(./*[1]) = "responseIf"] [count(./responseIf/*) = 2] [name(./responseIf/*[1]) = "not"] [name(./responseIf/not/*[1]) = "isNull"] [name(./responseIf/not/isNull/*[1]) = "variable"] [name(./responseIf/*[2]) = "setOutcomeValue"] [name(./responseIf/setOutcomeValue/*[1]) = "sum"] [name(./responseIf/setOutcomeValue/sum/*[1]) = "variable"] [name(./responseIf/setOutcomeValue/sum/*[2]) = "mapResponsePoint"]'

        sub_pattern_feedback_operator_if = '[name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [contains(name(./responseIf/*[1]/*[1]), "map")] [name(./responseIf/*[1]/*[2]) = "baseValue" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ]'
        sub_pattern_feedback_else = '[name(./*[2]) = "responseElse"] [count(./responseElse/*) = 1 ] [name(./responseElse/*[1]) = "setOutcomeValue"] [name(./responseElse/setOutcomeValue/*[1]) = "baseValue"]';
        sub_pattern_feedback_correct = '[name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "match" ] [name(./responseIf/*[1]/*[1]) = "variable" ] [name(./responseIf/*[1]/*[2]) = "correct" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ]'
        sub_pattern_feedback_incorrect = '[name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "not" ] [count(./responseIf/not) = 1 ] [name(./responseIf/not/*[1]) = "match" ] [name(./responseIf/not/*[1]/*[1]) = "variable" ] [name(./responseIf/not/*[1]/*[2]) = "correct" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ]'
        sub_pattern_feedback_match_choices = '[name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "match" ] [name(./responseIf/*[1]/*[2]) = "multiple" ] [name(./responseIf/*[1]/*[2]/*) = "baseValue" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ] '
        sub_pattern_feedback_match_choices_empty = '[name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "match" ] [name(./responseIf/*[1]/*[2]) = "multiple" ] [count(./responseIf/*[1]/*[2]/*) = 0 ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ] '
        sub_pattern_feedback_match_choice = '[name(./*[1]) = "responseIf" ] [count(./responseIf/*) = 2 ] [name(./responseIf/*[1]) = "match" ] [name(./responseIf/*[1]/*[2]) = "baseValue" ] [name(./responseIf/*[2]) = "setOutcomeValue" ] [name(./responseIf/setOutcomeValue/*[1]) = "baseValue" ] '
        pattern_feedback_operator = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_operator_if
        pattern_feedback_operator_with_else = '/responseCondition [count(./*) = 2 ]' + sub_pattern_feedback_operator_if + sub_pattern_feedback_else
        pattern_feedback_correct = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_correct
        pattern_feedback_correct_with_else = '/responseCondition [count(./*) = 2 ]' + sub_pattern_feedback_correct + sub_pattern_feedback_else
        pattern_feedback_incorrect = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_incorrect
        pattern_feedback_incorrect_with_else = '/responseCondition [count(./*) = 2 ]' + sub_pattern_feedback_incorrect + sub_pattern_feedback_else
        pattern_feedback_match_choices = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_match_choices
        pattern_feedback_match_choices_with_else = '/responseCondition [count(./*) = 2 ]' + sub_pattern_feedback_match_choices + sub_pattern_feedback_else
        pattern_feedback_match_choice = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_match_choice
        pattern_feedback_match_choices_empty = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_match_choices_empty
        pattern_feedback_match_choices_empty_with_else = '/responseCondition [count(./*) = 2 ]' + sub_pattern_feedback_match_choices_empty + sub_pattern_feedback_else
        pattern_feedback_match_choice = '/responseCondition [count(./*) = 1 ]' + sub_pattern_feedback_match_choice
        pattern_feedback_match_choice_with_else = '/responseCondition [count(./*) = 2 ]' + sub_pattern_feedback_match_choice + sub_pattern_feedback_else

        rules = {}
        simple_feedback_rules = {}

        for response_rule in data:
            feedback_rule = None
            subtree = response_rule

            if len(subtree.xpath(pattern_correct)) > 0:
                response_identifier = subtree.responseIf.match.variable['identifier']
                rules[response_identifier] = Template.MATCH_CORRECT
            elif len(subtree.xpath(pattern_mapping)) > 0:
                response_identifier = subtree.responseIf.match.variable['identifier']
                rules[response_identifier] = Template.MAP_RESPONSE
            elif len(subtree.xpath(pattern_mapping_point)) > 0:
                response_identifier = subtree.responseIf.match.variable['identifier']
                rules[response_identifier] = Template.MAP_RESPONSE_POINT
            elif len(subtree.xpath(pattern_feedback_correct)) > 0 or len(subtree.xpath(pattern_feedback_correct_with_else)) > 0:
                feedback_rule = self.build_simple_feedback_rule(subtree, 'correct')
            elif len(subtree.xpath(pattern_feedback_incorrect)) > 0 or len(subtree.xpath(pattern_feedback_incorrect_with_else)) > 0:
                response_identifier = subtree.responseIf.match.variable['identifier']
                feedback_rule = self.build_simple_feedback_rule(subtree, 'incorrect', None, response_identifier)
            elif len(subtree.xpath(pattern_feedback_operator)) > 0 or len(subtree.xpath(pattern_feedback_operator_with_else)) > 0:
                operator = ''
                value = ''
                for child in subtree.responseIf.getchildren():
                    operator = child.get_name()
                    map = None
                    for grand_child in child.getchildren():
                        map = grand_child.get_name()
                        response_identifier = grand_child.get('identifier')
                        break
                    value = child.base_value
                    break
                feedback_rule = self.build_simple_feedback_rule(subtree, operator, value)
            elif len(subtree.xpath(pattern_feedback_match_choices)) > 0 or len(subtree.xpath(pattern_feedback_match_choices_with_else)) > 0 \
                or len(subtree.xpath(pattern_feedback_match_choices_empty)) > 0 or len(subtree.xpath(pattern_feedback_match_choices_empty_with_else)) > 0:
                choices = []
                for choice in subtree.responseIf.match.muliple.baseValue:
                    choices.append(choice)
                feedback_rule = self.build_simple_feedback_rule(subtree, 'choices', choices)
            elif len(subtree.xpath(pattern_feedback_match_choice)) > 0 or len(subtree.xpath(pattern_feedback_match_choice_with_else)) > 0:
                choices = [subtree.responseIf.match.baseValue]
                feedback_rule = self.build_simple_feedback_rule(subtree, 'choices', choices)
            else:
                raise ValueError()

            if feedback_rule is not None:
                response_identifier = feedback_rule.get_compared_outcome().get_identifier()
                if response_identifier not in simple_feedback_rules:
                    simple_feedback_rules[response_identifier] = []
                simple_feedback_rules[response_identifier].append(feedback_rule)

        response_identifiers = []
        for interaction in interactions:
            interaction_response = interaction.get_response()
            response_identifier = interaction_response.get_identifier()
            response_identifiers.append(response_identifier)

            if response_identifier in simple_feedback_rules:
                for rule in simple_feedback_rules[response_identifier]:
                    interaction_response.add_feedback_rule(rule)

        if len(set(rules.keys()) - set(response_identifiers)) > 0:
            raise ValueError()

        template_driven_response_processing = TemplatesDriven()
        for interaction in interactions:
            if interaction.get_response().get_identifier() in rules:
                pattern = rules[interaction.get_response().get_identifier()]
            else:
                pattern = Template.NONE
            template_driven_response_processing.set_template(interaction.get_response(), pattern)
        template_driven_response_processing.set_related_item(self.item)

        return template_driven_response_processing

    def build_custom_response_processing(self, data):
        response_rules = []
        custom = Custom(response_rules, data)
        return custom

    def build_simple_feedback_rule(self, subtree, condition_name, compared_value=None, response_id=''):
        if response_id == '':
            response_identifier = subtree.responseIf.match.variable['identifier']
        else:
            response_identifier = response_id
        feedback_outcome_identifier = subtree.responseIf.setOutcomeValue['identifier']
        feedback_identifier = subtree.responseIf.setOutcomeValue.baseValue

        try:
            response = self.get_response(response_identifier)
            outcome = self.get_outcome(feedback_outcome_identifier)
            feedback_then = self.get_modal_feedback(feedback_identifier)

            feedback_else = None
            if subtree.responseIf.get_name():
                feedback_else_identifier = subtree.responseIf.setOutcomeValue.baseValue
                feedback_else = self.get_modal_feedback(feedback_identifier)

            feedback_rule = SimpleFeedbackRule(outcome, feedback_then, feedback_else)
            feedback_rule.set_condition(response, condition_name, compared_value)
        except ValueError:
            raise ValueError()

        return feedback_rule

    def get_modal_feedback(self, identifier):
        for feedback in self.item.get_modal_feedbacks():
            if feedback.get_identifier() == identifier:
                return feedback
        raise ValueError()

    def get_outcome(self, identifier):
        for outcome in self.item.get_outcomes():
            if outcome.get_identifier() == identifier:
                return outcome
        raise ValueError()

    def get_response(self, identifier):
        for response in self.item.get_responses():
            if response.get_identifier() == identifier:
                return response
        raise ValueError()










