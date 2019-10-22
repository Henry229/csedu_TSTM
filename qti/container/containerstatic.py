from .container import Container


class ContainerStatic(Container):
    def get_valid_element_types(self):
        return [
            'Img', 'Table', 'Math', 'Feedback', 'Object', 'XInclude'
        ]

    def get_body(self):
        return self.fix_non_void_tags(super().get_body())
