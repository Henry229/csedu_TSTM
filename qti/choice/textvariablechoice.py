from .choice import Choice
from ..outcomedeclaration import OutcomeDeclaration


class TextVariableChoice(Choice):
    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.text = ''

    def get_content(self):
        return self.text

    def set_content(self, content):
        if content is None:
            content = str(content)
        if isinstance(content, str):
            self.text = content
        elif isinstance(content, OutcomeDeclaration):
            self.text = content
        else:
            raise ValueError()

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['body'] = self.text
        return variables

    def to_dict(self, filter_variable_content=False, filtered=None):
        value = super().to_dict(filter_variable_content, filtered)
        value['text'] = self.text
        return value

