from .enumeration import Enumeration


class Orientation(Enumeration):
    @staticmethod
    def get_enumeration():
        return ['vertical', 'horizontal']
