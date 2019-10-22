from .identifier import Identifier


class IdentifierResponse(Identifier):

    @staticmethod
    def get_allowed_classes():
        return [
            'ResponseDeclaration'
        ]
