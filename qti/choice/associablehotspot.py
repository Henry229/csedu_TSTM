from .hotspot import Hotspot


class AssociableHotspot(Hotspot):
    qtiTagName = 'associableHotspot'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'MatchMax', "MatchMin"
        ]

    def get_template_html(self):
        template = 'choices/' + self.__class__.__name__.lower() + '.html'
        return template

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': is not implemented')
