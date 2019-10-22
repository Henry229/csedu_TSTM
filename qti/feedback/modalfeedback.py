from .feedback import Feedback


class ModalFeedback(Feedback):
    qtiTagName = 'modalFeedback'

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'TitleOptional'
        ]

    def to_form(self):
        return ''

