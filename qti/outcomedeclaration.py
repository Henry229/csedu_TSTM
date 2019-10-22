
from .variabledeclaration import VariableDeclaration


class OutcomeDeclaration(VariableDeclaration):
    qtiTagName = 'outcomeDeclaration'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'View', 'Interpretation', 'LongInterpretation', 'NormalMaximum',
            'NormalMinimum', 'MasteryValue'
        ]

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['default_value'] = self.get_default_value()
        return data

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['default_value'] = None
        default_value = self.get_default_value()
        if default_value is not None and default_value.strip() != '':
            variables['default_value'] = default_value

        return variables

    def to_json(self):
        return ''



