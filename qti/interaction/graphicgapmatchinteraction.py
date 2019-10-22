from .objectinteraction import ObjectInteraction
from ..choice.choice import Choice
from ..choice.gapimg import GapImg
from ..utils import ClassUtils


class GraphicGapMatchInteraction(ObjectInteraction):
    qtiTagName = 'graphicGapMatchInteraction'
    choiceClass = 'AssociableHotspot'
    baseType = 'directedPair'

    def __init__(self, attributes=None, related_item=None, serial=''):
        super().__init__(attributes, related_item, serial)
        self.gapImgs = {}

    def create_gap_img(self, object_label='', object_attributes=None):
        if object_attributes is None:
            object_attributes = {}
        gap_img = None
        if self.choiceClass != '' and ClassUtils.is_subclass_by_name(self.choiceClass, Choice):
            attributes = {'objectLabel': object_label} if object_label != '' else {}
            gap_img = GapImg(attributes)
            gap_img.set_content(ObjectInteraction(object_attributes))
            self.add_gap_img(gap_img)

        return gap_img

    def add_gap_img(self, gap_img: GapImg):
        self.gapImgs[gap_img.get_serial()] = gap_img
        related_item = self.get_related_item()
        if related_item is not None:
            gap_img.set_related_item(related_item)

    def get_gap_imgs(self):
        return self.gapImgs

    def get_identified_elements(self):
        elements = super().get_identified_element()
        elements.add_multiple(self.get_gap_imgs())
        return elements

    def to_dict(self, filter_variable_content=False, filtered=None):
        data = super().to_dict(filter_variable_content, filtered)
        data['gapImgs'] = self.get_dict_serialized_element_collection(self.get_gap_imgs(),
                                                                      filter_variable_content, filtered)
        return data

    # @staticmethod
    # def get_template_qti():
    #     return ''

    def get_template_qti_variables(self):
        variables = super().get_template_qti_variables()
        variables['gapImgs'] = ''
        for gap_img in self.get_gap_imgs().values():
            variables['gapImgs'] += gap_img.to_qti()
        return variables

    def get_choice_by_serial(self, serial):
        choice = super().get_choice_by_serial()
        if choice is None:
            gap_imgs = self.get_gap_imgs()
            if serial in gap_imgs:
                choice = gap_imgs[serial]
        return choice

    def remove_choice(self, choice, set_number=None):
        if isinstance(choice, GapImg):
            del self.gapImgs[choice.get_serial()]
        else:
            super().remove_choice(choice)

    def get_template_html_variables(self):
        variables = super().get_template_html_variables()
        variables['prompt'] = self.get_prompt_object().to_html()
        gap_imgs = []
        for img in self.get_gap_imgs().values():
            gap_imgs.append(img.to_html())
        variables['gapImgs'] = gap_imgs
        variables['svg'] = self.build_svg()
        return variables

    def to_html(self, interaction=None):
        template = 'interactions/graphicgapmatchinteraction.html'
        variables = self.get_template_html_variables()
        html_rendered = self.render_item_html_template(template, variables)
        return html_rendered

    def build_svg(self):
        template = 'interactions/objectsvg.html'
        variables = self.get_object_variables()
        svg_rendered = self.render_item_html_template(template, variables)
        return svg_rendered
