from .element import Element


class InfoControl(Element):
    qtiTagName = 'infoControl'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.typeIdentifier = ''
        self.markup = ''

    def get_used_attributes(self):
        return ['Title']

    def get_markup(self):
        return self.markup

    def set_markup(self, markup):
        self.markup = markup

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['typeIdentifier'] = self.typeIdentifier
        data['markup'] = self.markup

        return data

    @classmethod
    def get_template_qti(cls):
        return cls.get_template_path() + 'interactions/infocontrolinteraction.xml'

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['typeIdentifier'] = self.typeIdentifier
        variables['markup'] = self.markup

        return variables

    def feed(self, parser, data):
        markup = parser.get_body_data(data[0], True)
        self.set_markup(markup)
