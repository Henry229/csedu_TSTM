from jinja2 import Environment, PackageLoader, select_autoescape


class ItemRenderer:
    def __init__(self, template_path, variables=None):
        if variables is None:
            variables = {}
        self.variables = variables

        env = Environment(
            loader=PackageLoader('qti.itemrenderer', 'templates'),
            autoescape=select_autoescape([]),
            trim_blocks=True, lstrip_blocks=True
        )
        self.template = env.get_template(template_path)

    def render(self):
        return self.template.render(self.variables)
