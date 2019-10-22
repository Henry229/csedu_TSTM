
from .containerinteractive import ContainerInteractive


class ContainerItemBody(ContainerInteractive):
    def get_valid_element_types(self):
        return [
            'Img', 'Table', 'Math', 'Feedback', 'Object', 'Interaction', 'RubricBlock',
            'InfoControl', 'XInclude'
        ]
