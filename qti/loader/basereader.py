class BaseReader:
    """
    Class for Base parser
    """
    def __init__(self, source_type, source, options=None):
        if options is None:
            options = {}
        self.data = None
        self.valid = False
        self.sourceType = source_type
        self.source = source
        self.file_extension = options.get('extension', 'xml')

    def validate(self, schema=''):
        # ToDO: implement schema validation
        self.valid = True
        return self.valid





