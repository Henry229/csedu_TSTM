from .element import Element


class Stylesheet(Element):
    qtiTagName = 'stylesheet'

    def get_used_attributes(self):
        return [
            'Href', 'Type', 'Media', 'TitleOptional'
        ]
