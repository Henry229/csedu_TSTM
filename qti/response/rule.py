
class RuleMixin:
    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_rule(self):
        raise NotImplementedError()
