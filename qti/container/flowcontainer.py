
class FlowContainerMixin:
    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_body(self):
        raise NotImplementedError()
