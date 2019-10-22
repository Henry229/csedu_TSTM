from ..identifiedelement import IdentifiedElement


class Choice(IdentifiedElement):

    def get_used_attributes(self):
        return [
            'Fixed', 'TemplateIdentifier', 'ShowHideChoice'
        ]

    def get_content(self):
        raise NotImplementedError()

    def set_content(self, content):
        raise NotImplementedError()

    def is_identifier_available(self, identifier):
        valid = False
        if self.identifier != '' and self.identifier == identifier:
            valid = True
        else:
            related_item = self.get_related_item()
            if related_item is None:
                valid = True
            else:
                collection = related_item.get_identified_elements()
                unique_choice = collection.get_unique(identifier, 'Choice')
                unique_outcome = collection.get_unique(identifier, 'OutcomeDeclaration')
                if unique_choice is None and unique_outcome is None:
                    valid = True
        return valid

    def get_template_html(self):
        template = 'choices/' + self.__class__.__name__.lower() + '.html'
        return template

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': is not implemented')
