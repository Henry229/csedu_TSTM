from .blockinteraction import BlockInteraction
from ..choice import get_choice_class, create_choice_class_object
from ..element import Element
from ..identifiercollection import IdentifierCollection
from ..utils import ClassUtils


class MatchInteraction(BlockInteraction):
    qtiTagName = 'matchInteraction'
    choiceClass = 'SimpleAssociableChoice'
    baseType = 'directedPair'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.choices = {0: {}, 1: {}}

    def get_identified_elements(self):
        elements = IdentifierCollection()
        elements.add_multiple(self.get_choices(0))
        elements.add_multiple(self.get_choices(1))
        return elements

    def get_used_attributes(self):
        return super().get_used_attributes() + [
            'Shuffle', 'MaxAssociations', 'MinAssociations'
        ]

    def get_choice_by_serial(self, serial):
        choice = None

        for c in self.choices.values():
            if serial in c:
                choice = c[serial]
                break
        return choice

    def is_valid_match_set_number(self, set_number):
        valid = False
        if set_number in self.choices:
            valid = True
        return valid

    def get_choices(self, set_number=None):
        if self.is_valid_match_set_number(set_number):
            return self.choices[set_number]
        else:
            return self.choices

    def add_choice(self, choice, set_number=None):
        result = False
        if self.is_valid_match_set_number(set_number):
            if MatchInteraction.choiceClass != '' and choice.__class__.__name__ == MatchInteraction.choiceClass:
                self.choices[set_number][choice.get_serial()] = choice
                related_item = self.get_related_item()
                if related_item is not None:
                    choice.set_related_item(related_item)
                result = True
            else:
                raise ValueError()
        return result

    def create_choice(self, choice_attributes=None, choice_value=None, set_number=None):
        choice = None
        if self.is_valid_match_set_number(set_number):
            if ClassUtils.is_subclass_by_name(get_choice_class(MatchInteraction.choiceClass)(), 'Choice'):
                choice = create_choice_class_object(MatchInteraction.choiceClass, choice_attributes, choice_value)
                self.add_choice(choice, set_number)

        return choice

    def remove_choice(self, choice, set_number=None):
        if set_number is not None:
            if set_number in self.choices:
                del self.choices[set_number][choice.get_serial()]
        else:
            for i, _ in self.choices.items():
                self.remove_choice(choice, i)

    def get_composing_elements(self, class_name=''):
        if class_name == '':
            class_name = 'Element'
        elements = super().get_composing_elements(class_name)

        for choice in self.get_choices(0).values():
            if isinstance(choice, Element):
                if ClassUtils.is_subclass_by_name(choice, class_name):
                    elements[choice.get_serial()] = choice
                elements = elements + choice.get_composing_elements(class_name)
        for choice in self.get_choices(1).values():
            if isinstance(choice, Element):
                if ClassUtils.is_subclass_by_name(choice, class_name):
                    elements[choice.get_serial()] = choice
                elements = elements + choice.get_composing_elements(class_name)

        return elements

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = {
            'serial': self.get_serial(),
            'qtiClass': self.get_qti_tag(),
            'attributes': self.get_attribute_values(),
            'prompt': self.get_prompt().to_dict(filter_variable_content, filtered),
            'choices': [
                self.get_dict_serialized_element_collection(self.get_choices(0), filter_variable_content, filtered),
                self.get_dict_serialized_element_collection(self.get_choices(1), filter_variable_content, filtered)
            ]
        }
        return data

    def get_template_qti_variables(self):
        variables = {
            'tag': self.qtiTagName,
            'attributes': self.get_attribute_values(),
            'prompt': self.prompt.to_qti()
        }
        if 'identifier' in variables['attributes']:
            del variables['attributes']['identifier']

        if self.get_prompt().get_body().strip() != '':
            variables['prompt'] = self.prompt.to_qti()

        choices = ''
        for i in range(2):
            choices += '<simpleMatchSet>'
            for choice in self.get_choices(i).values():
                choices += choice.to_qti()
            choices += '</simpleMatchSet>'

        variables['choices'] = choices

        return variables

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        choices = []
        for choice in self.get_choices(0).values():
            choices.append(choice.to_html(self))
        variables['matchSet1'] = choices
        choices = []
        for choice in self.get_choices(1).values():
            choices.append(choice.to_html(self))

        variables['matchSet2'] = choices

        return variables

    def to_html(self, interaction=None):
        template = 'interactions/matchinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered
