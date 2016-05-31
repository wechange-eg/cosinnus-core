# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from django import forms

from wagtail.wagtailcore.fields import RichTextField, RichTextArea
from wagtail.wagtailcore.rich_text import DbWhitelister

from django.utils.functional import cached_property
from wagtail.wagtailcore.blocks.field_block import RichTextBlock, RawHTMLBlock,\
    URLBlock
from wagtail.wagtailcore import blocks
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailcore.blocks.struct_block import StructBlock
from wagtail.wagtailembeds.blocks import EmbedBlock

    

class BetterDbWhitelister(DbWhitelister):
    """ Prevents <div> tags from being replaced by <p> """
    
    @classmethod
    def clean_tag_node(cls, doc, tag):
        if not 'data-embedtype' in tag.attrs and tag.name == 'div':
            super(DbWhitelister, cls).clean_tag_node(doc, tag) # this gets around having the 'div' tag replaced
        else:
            super(BetterDbWhitelister, cls).clean_tag_node(doc, tag)
            

class BetterRichTextArea(RichTextArea):
    """ Enables using a custom DbWhitelister """
    
    def value_from_datadict(self, data, files, name):
        original_value = super(RichTextArea, self).value_from_datadict(data, files, name)
        if original_value is None:
            return None
        return BetterDbWhitelister.clean(original_value)


class BetterRichTextField(RichTextField):
    """ Enables using a custom DbWhitelister """
    
    def formfield(self, **kwargs):
        defaults = {'widget': BetterRichTextArea}
        defaults.update(kwargs)
        return super(RichTextField, self).formfield(**defaults) # super on RichTextField, not self.__class__!


class BetterRichTextBlock(RichTextBlock):
    """ Enables using a custom DbWhitelister """
    
    @cached_property
    def field(self):
        return forms.CharField(widget=BetterRichTextArea, **self.field_options)

    
    
class CreateProjectButtonBlock(StructBlock):
    
    class Meta:
        label = _('Create-Project or Group Button')
        icon = 'group'
        template = 'cosinnus/wagtail/widgets/create_project_button.html'
        
    type = blocks.ChoiceBlock(choices=[
        ('project', 'Project'),
        ('group', 'Group'),
    ], required=True, label='Type', default='project')


    def get_context(self, value):
        context = super(CreateProjectButtonBlock, self).get_context(value)
        context['type'] = value.get('type')
        return context
    

class LinkBlock(StructBlock):
    url = blocks.URLBlock(label='URL')
    text = blocks.CharBlock()

    class Meta:
        icon = 'anchor'
        template = 'cosinnus/wagtail/widgets/link.html'

    def get_context(self, value):
        context = super(LinkBlock, self).get_context(value)
        context['href'] = value.get('url')
        context['text'] = value.get('text')
        context['class'] = value.get('cls')
        return context
    

""" Default configuration of available blocks for out StreamField, because DRY """
STREAMFIELD_BLOCKS_NOFRAMES = [
    ('paragraph', BetterRichTextBlock(icon='form')),
    ('image', ImageChooserBlock(icon='image')),
    ('create_project_button', CreateProjectButtonBlock()),    
    ('media', EmbedBlock(icon="media")),
    ('html', RawHTMLBlock(icon="code")),
    ('link', LinkBlock(icon="link")),
]
    

class DoubleFrameBlock(StructBlock):
    
    left = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')
    right = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')

    class Meta:
        icon = 'fa fa-text'
        template = 'cosinnus/wagtail/widgets/double_frame.html'
    
    def get_context(self, value):
        context = super(DoubleFrameBlock, self).get_context(value)
        context['left'] = value.get('left')
        context['right'] = value.get('right')
        return context

class TripleFrameBlock(StructBlock):
    
    left = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')
    middle = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')
    right = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')

    class Meta:
        icon = 'fa fa-text'
        template = 'cosinnus/wagtail/widgets/triple_frame.html'
    
    def get_context(self, value):
        context = super(TripleFrameBlock, self).get_context(value)
        context['left'] = value.get('left')
        context['middle'] = value.get('middle')
        context['right'] = value.get('right')
        return context
    
class QuadFrameBlock(StructBlock):
    
    left = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')
    middle_left = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')
    middle_right = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')
    right = blocks.StreamBlock(STREAMFIELD_BLOCKS_NOFRAMES, icon='cogs')

    class Meta:
        icon = 'fa fa-text'
        template = 'cosinnus/wagtail/widgets/quad_frame.html'
    
    def get_context(self, value):
        context = super(QuadFrameBlock, self).get_context(value)
        context['left'] = value.get('left')
        context['middle_left'] = value.get('middle_left')
        context['middle_right'] = value.get('middle_right')
        context['right'] = value.get('right')
        return context

 
STREAMFIELD_BLOCKS = STREAMFIELD_BLOCKS_NOFRAMES + [   
    ('frame_2x1', DoubleFrameBlock(icon="form")),
    ('frame_3x1', TripleFrameBlock(icon="form")),
    ('frame_4x1', QuadFrameBlock(icon="form")),
]

    