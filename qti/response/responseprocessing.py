from ..contentvariable import ContentVariableMixin
from ..element import Element


class ResponseProcessing(ContentVariableMixin, Element):
    qtiTagName = 'responseProcessing'

    @staticmethod
    def create(item):
        raise NotImplementedError()

    @staticmethod
    def takeover_form(response_processing, item):
        raise NotImplementedError()

    def get_form(self, response):
        return None

    def take_notice_of_Added_interaction(self, interaction, item):
        pass

    def take_notice_of_removed_interaction(self, interaction, item):
        pass

    def get_used_attributes(self):
        return {}

    def to_filtered_dict(self):
        return self.to_dict()
