
class ClassUtils:
    @staticmethod
    def is_subclass_by_name(this_class_obj, subclass_of_name):
        import inspect
        if subclass_of_name == 'object':
            return True
        for cls in inspect.getmro(this_class_obj.__class__):
            if cls.__name__ == subclass_of_name:
                return True
        return False
