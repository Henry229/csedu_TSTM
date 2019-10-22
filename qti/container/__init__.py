
def get_class_dict():
    from .containergap import ContainerGap
    from .containerhottext import ContainerHottext
    class_dict = {
        'ContainerHottext': ContainerHottext,
        'ContainerGap': ContainerGap,
    }
    return class_dict


def create_container_class_object(class_name, attributes=None, related_item=None, serial=''):
    cls = get_class_dict().get(class_name)
    if cls:
        return cls(attributes, related_item, serial)
    return None


def get_container_class(class_name):
    return get_class_dict().get(class_name)


def is_valid_container_class(class_name):
    return get_class_dict().get(class_name) is not None
