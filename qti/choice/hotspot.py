from .choice import Choice


class Hotspot(Choice):
    def set_content(self, content):
        self.set_attribute('shape', content)

    def get_content(self):
        return self.get_attribute('shape')

    def validate_coords(self, new_attributes=None):
        if new_attributes is None:
            new_attributes = {}

        valid = True
        shape = ''
        if 'shape' in new_attributes:
            shape = new_attributes['shape']
        else:
            s = self.get_attribute('shape')
            if s is not None:
                shape = s

        if 'coords' in new_attributes:
            coords = new_attributes['coords']
            if type(coords) is list:
                pass
            elif type(coords) is str:
                coords = coords.split(',')
            else:
                raise ValueError()

            if shape != '':
                if shape == 'rect':
                    valid = len(coords) == 4
                elif shape == 'circle':
                    valid = len(coords) == 3
                elif shape == 'ellipse':
                    valid = len(coords) == 4
                elif shape == 'poly':
                    valid = len(coords) % 2 == 0

        return valid

    def get_template_html(self):
        template = 'choices/' + self.__class__.__name__.lower() + '.html'
        return template

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': is not implemented')