import re

from lxml import etree


class QtiSerializer:
    @staticmethod
    def parse_element_xml(xml) -> dict:
        attributes = {}
        for name, value in xml.attrib.items():
            name = simple_name(name)
            attributes[name] = value

        tag = simple_name(xml.tag)
        parsed = {
            'qtiClass': tag,
        }
        if attributes:
            parsed['attributes'] = attributes

        return parsed

    @staticmethod
    def parse_expression_xml(xml):
        parsed = QtiSerializer.parse_element_xml(xml)
        value = etree.tostring(xml)
        expressions = []
        for child in xml.getchildren():
            if child.__class__.__name__ == '_Comment':
                continue
            expressions.append(QtiSerializer.parse_expression_xml(child))
        if expressions:
            parsed['expressions'] = expressions
        if len(value):
            parsed['value'] = value
        return parsed

    @staticmethod
    def parse_response_rule_xml(xml):
        parsed = QtiSerializer.parse_element_xml(xml)
        for child in xml.getchildren():
            if child.__class__.__name__ == '_Comment':
                continue
            parsed['expression'] = QtiSerializer.parse_expression_xml(child)
        return parsed

    @staticmethod
    def parse_response_processing_fragment_xml(xml):
        return QtiSerializer.parse_response_rules_container_xml(xml)

    @staticmethod
    def parse_response_if_xml(xml):
        parsed = QtiSerializer.parse_element_xml(xml)
        i = 0
        expression = None
        response_rules = []
        for child in xml.getchildren():
            if child.__class__.__name__ == '_Comment':
                continue
            if i == 0:
                expression = QtiSerializer.parse_expression_xml(xml)
            else:
                name = simple_name(child.tag)
                method_name = get_parse_method(name)
                if method_name is not None:
                    response_rules.append(method_name(child))
                else:
                    response_rules.append(QtiSerializer.parse_response_rule_xml(child))
            i += 1
        parsed['expression'] = expression
        parsed['responseRules'] = response_rules
        return parsed

    @staticmethod
    def parse_response_else_xml(xml):
        return QtiSerializer.parse_response_rules_container_xml(xml)

    @staticmethod
    def parse_response_condition_xml(xml):
        parsed = QtiSerializer.parse_element_xml(xml)
        namespace = xml.nsmap.get(None, '')
        if namespace != '':
            namespace = '{' + namespace + '}'
        for response_if_xml in findall(namespace + 'responseIf', xml):
            parsed['responseIf'] = QtiSerializer.parse_response_if_xml(response_if_xml)
            break
        for response_if_xml in findall(namespace + 'responseElseIf', xml):
            if 'responseElseIfs' not in parsed:
                parsed['responseElseIfs'] = []
            parsed['responseElseIfs'].append(QtiSerializer.parse_response_if_xml(response_if_xml))
        for response_if_xml in findall(namespace + 'responseElse', xml):
            parsed['responseElse'] = QtiSerializer.parse_response_else_xml(response_if_xml)
            break

        return parsed

    @staticmethod
    def parse_response_rules_container_xml(xml):
        parsed = QtiSerializer.parse_element_xml(xml)
        response_rules = []
        for child in xml.getchildren():
            if child.__class__.__name__ == '_Comment':
                continue
            name = simple_name(child.tag)
            method_name = get_parse_method(name)
            if method_name is not None:
                response_rules.append(method_name(child))
            else:
                response_rules.append(QtiSerializer.parse_response_rule_xml(child))

        parsed['responseRules'] = response_rules
        return parsed

    @staticmethod
    def parse_response_processing_xml(xml):
        return QtiSerializer.parse_response_rules_container_xml(xml)


def simple_name(long_name):
    return re.sub(r'{.+?}', '', long_name)


def get_parse_method(tag_name):
    methods = {
        'element': QtiSerializer.parse_element_xml,
        'expression': QtiSerializer.parse_expression_xml,
        'responseRule': QtiSerializer.parse_response_rule_xml,
        'responseRulesContainer': QtiSerializer.parse_response_rules_container_xml,
        'responseProcessingFragment': QtiSerializer.parse_response_processing_fragment_xml,
        'responseIf': QtiSerializer.parse_response_if_xml,
        'responseElse': QtiSerializer.parse_response_else_xml,
        'responseCondition': QtiSerializer.parse_response_condition_xml,
        'responseProcessing': QtiSerializer.parse_response_processing_xml,
    }
    return methods.get(tag_name)


def findall(tag_name, context_node=None):
    return context_node.findall(tag_name)
