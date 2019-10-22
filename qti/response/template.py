from lxml import etree

from .responseprocessing import ResponseProcessing
from .rule import RuleMixin
from ..renderer.templaterendere import TemplateRenderer
from ..serializer.qtiserializer import QtiSerializer


class Template(RuleMixin, ResponseProcessing):
    MATCH_CORRECT = 'http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct'
    MAP_RESPONSE = 'http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response'
    MAP_RESPONSE_POINT = 'http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response_point'
    MATCH_CORRECT_qtiv2p0 = 'http://www.imsglobal.org/question/qti_v2p0/rptemplates/match_correct'
    MAP_RESPONSE_qtiv2p0 = 'http://www.imsglobal.org/question/qti_v2p0/rptemplates/map_response'
    MAP_RESPONSE_POINT_qtiv2p0 = 'http://www.imsglobal.org/question/qti_v2p0/rptemplates/map_response_point'
    MATCH_CORRECT_qtiv2p2 = 'http://www.imsglobal.org/question/qti_v2p2/rptemplates/match_correct'
    MAP_RESPONSE_qtiv2p2 = 'http://www.imsglobal.org/question/qti_v2p2/rptemplates/map_response'
    MAP_RESPONSE_POINT_qtiv2p2 = 'http://www.imsglobal.org/question/qti_v2p2/rptemplates/map_response_point'
    NONE = 'no_response_processing'

    def __init__(self, uri):
        self.file = ''
        if uri in [self.MATCH_CORRECT, self.MATCH_CORRECT_qtiv2p0, self.MATCH_CORRECT_qtiv2p2]:
            self.uri = self.MATCH_CORRECT
        elif uri in [self.MAP_RESPONSE, self.MAP_RESPONSE_qtiv2p0, self.MAP_RESPONSE_qtiv2p2]:
            self.uri = self.MAP_RESPONSE
        elif uri in [self.MAP_RESPONSE_POINT, self.MAP_RESPONSE_POINT_qtiv2p0, self.MAP_RESPONSE_POINT_qtiv2p2]:
            self.uri = self.MAP_RESPONSE_POINT
        elif uri in []:
            self.uri = self.NONE
        else:
            raise ValueError()

        super().__init__()

    def to_qti(self):
        value = ''
        if self.uri != self.NONE:
            renderer = TemplateRenderer('rptemplate.xml', {'uri': self.uri})
            value = renderer.render()
        return value

    def get_rule(self):
        # ToDo: not implemented
        return self.uri

    def get_template_content(self):
        import os
        basedir = os.path.abspath(os.path.dirname(__file__))

        content = ''
        template_path = ''
        standard_template_folder = os.path.join(basedir, '../data/qtiv2p1/rptemplates/')
        if self.uri == self.MATCH_CORRECT:
            template_path = standard_template_folder + 'match_correct.xml'
        elif self.uri == self.MAP_RESPONSE:
            template_path = standard_template_folder + 'map_response.xml'
        elif self.uri == self.MAP_RESPONSE_POINT:
            template_path = standard_template_folder + 'map_response_content.xml'
        elif self.uri == self.NONE:
            content = b''
        else:
            raise ValueError()

        if template_path != '':
            with open(template_path, 'rb') as f:
                content = f.read()
        return content

    def get_uri(self):
        return self.uri

    def to_dict(self, filter_variable_content=False, filtered=None):
        result = super().to_dict(filter_variable_content, filtered)
        content = self.get_template_content()
        serialized = QtiSerializer.parse_response_processing_xml(etree.XML(content))
        protected_data = {
            'processing_type': 'template',
            'data': self.uri,
            'response_rules': serialized['responseRules']
        }

        if filter_variable_content:
            filtered[self.get_serial()] = protected_data
        else:
            result.update(protected_data)

        return result

    def get_used_attributes(self):
        return {}

