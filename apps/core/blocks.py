from wagtail import blocks


class ProgrammeSection(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False)
    heading = blocks.CharBlock()
    introduction = blocks.TextBlock(required=False)
    items = blocks.ListBlock(blocks.StructBlock([
        ('title', blocks.CharBlock()),
        ('text', blocks.TextBlock()),
    ]))
    layout = blocks.ChoiceBlock(choices=[('cards', 'Cards'), ('steps', 'Steps'), ('faq', 'Questions and answers')], default='cards')

    class Meta:
        template = 'core/blocks/programme_section.html'
        icon = 'list-ul'
