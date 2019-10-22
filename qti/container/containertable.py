from .container import Container


class ContainerTable(Container):

    def get_valid_element_types(self):
        return [
            'Img', 'Math', 'Feedback', 'Object', 'Interaction', 'RubricBlock', 'InfoControl',
            'XInclude'
        ]
