import re

from lxml import etree

from .responseprocessing import ResponseProcessing
from .rule import RuleMixin


class Custom(RuleMixin, ResponseProcessing):
    def __init__(self, response_rules, xml):
        self.responseRules = response_rules
        self.data = ''
        super().__init__()
        self.set_data(xml)

    def get_rule(self):
        rule = ''
        for response_rule in self.responseRules:
            rule += response_rule.get_rule()

        return rule

    def set_data(self, xml):
        self.data = xml

    def get_data(self):
        return self.data

    def to_dict(self, filter_variable_content=False, filtered=None):
        raise ValueError()

    def to_qti(self):
        xml_string = etree.tostring(self.get_data(), encoding='unicode')
        xml_string = re.sub(r'\s*xmlns[:]*\w*=\".+?\"', "", xml_string, flags=re.IGNORECASE)
        return xml_string

