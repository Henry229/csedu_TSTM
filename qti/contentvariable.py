class ContentVariableMixin:
    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_filtered_dict(self):
        raise NotImplementedError()
