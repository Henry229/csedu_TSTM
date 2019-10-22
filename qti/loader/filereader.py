
from .basereader import BaseReader


class FileReader(BaseReader):
    def __init__(self, source, options=None):
        super().__init__('file', source, options)

