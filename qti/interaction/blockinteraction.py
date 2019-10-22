import os

from .interaction import Interaction
from .prompt import Prompt


class BlockInteraction(Interaction):
    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.prompt = Prompt({}, related_item)

    def get_prompt(self):
        return self.prompt.get_body()

    def get_prompt_object(self):
        return self.prompt

    def set_prompt(self, body):
        self.prompt.get_body().edit(body)

    def to_dict(self, filter_variable_content=False, filtered=None):
        value = super().to_dict(filter_variable_content, filtered)
        value['prompt'] = self.get_prompt().to_dict(filter_variable_content, filtered)
        return value

    @classmethod
    def get_template_qti(cls):
        template_path = cls.get_template_path()
        tpl_name = 'interactions/' + cls.__name__.lower() + '.xml'
        template = os.path.join(template_path, tpl_name)
        if not os.path.exists(template):
            tpl_name = 'interactions/blockinteraction.xml'
        return tpl_name

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        if self.get_prompt().get_body().strip() != '':
            variables['prompt'] = self.prompt.to_qti()
        return variables

    def to_html(self, interaction=None):
        raise NotImplementedError(self.qtiTagName + ': to_html is not implemented')