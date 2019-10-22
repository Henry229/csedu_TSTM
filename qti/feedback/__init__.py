from .feedbackblock import FeedbackBlock
class_dict = {
    'FeedbackBlock': FeedbackBlock
}


def create_feedback_class_object(class_name, value=None, version=''):
    cls = class_dict.get(class_name)
    if cls:
        return cls(value, version)
    return None


def get_feedback_class(class_name):
    return class_dict.get(class_name)


def is_valid_feedback_class(class_name):
    return class_dict.get(class_name) is not None
