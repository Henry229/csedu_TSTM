
class Exportable:
    def to_qti(self):
        raise NotImplementedError("to_qti must be implemented")

    def to_dict(self, filter_variable_content=False, filtered=None):
        raise NotImplementedError("to_dict must be implemented")
