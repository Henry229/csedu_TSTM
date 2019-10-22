from ..element import Element
from ..responsedeclaration import ResponseDeclaration
from ..variabledeclaration import VariableDeclaration


class SimpleFeedbackRule(Element):
    def __init__(self, feedback_outcome, feedback_then=None, feedback_else=None):
        self.condition = 'correct'
        self.comparedOutcome = None
        self.comparedValue = 0.0
        self.feedbackThen = feedback_then
        self.feedbackElse = feedback_else
        self.feedbackOutcome = feedback_outcome

        super().__init__()

    def get_attributes(self):
        return self.attributes

    def get_feedback_outcome(self):
        return self.feedbackOutcome

    def get_compared_outcome(self):
        return self.comparedOutcome

    def get_feedback_else(self):
        return self.feedbackElse

    def get_condition(self):
        return self.condition

    def get_feedback_then(self):
        return self.feedbackThen

    def remove_feedback_else(self):
        self.feedbackElse = None

    def set_feedback_else(self, feedback):
        self.feedbackElse = feedback

    def set_condition(self, compared_outcome: VariableDeclaration, condition, compared_value=None):
        if condition in ['correct', 'incorrect']:
            if isinstance(compared_outcome, ResponseDeclaration):
                self.comparedOutcome = compared_outcome
                self.condition = condition
            else:
                raise ValueError()
        elif condition in ['lt', 'lte', 'equal', 'gte', 'gt']:
            if compared_value is not None:
                self.comparedOutcome = compared_outcome
                self.condition = condition
                self.comparedValue = compared_value
            else:
                raise ValueError()
        elif condition in ['choices']:
            if type(compared_value) is list:
                self.comparedOutcome = compared_outcome
                self.condition = condition
                self.comparedValue = compared_value
            else:
                raise ValueError()
        else:
            raise ValueError()

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = {
            'serial': self.get_serial(),
            'qtiClass': '_simpleFeedbackRule',
            'comparedOutcome': '' if self.comparedOutcome is None else self.comparedOutcome.get_serial(),
            'comparedValue': self.comparedValue,
            'condition': self.condition,
            'feedbackOutcome': '' if self.feedbackOutcome is None else self.feedbackOutcome.get_serial(),
            'feedbackThen': '' if self.feedbackThen is None else self.feedbackThen.get_serial(),
            'feedbackElse': '' if self.feedbackElse is None else self.feedbackElse.get_serial()
        }
        return data

    def to_qti(self):
        return ''

