
class IdentifiedElementContainerMixin:
    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_identified_elements(self):
        raise NotImplementedError()
