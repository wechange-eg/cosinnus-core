# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import wagtail.wagtailimages.blocks
import wagtail.wagtailcore.blocks
import wagtail.wagtailcore.fields
from django.conf import settings

import cosinnus.models.wagtail_blocks


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0009_auto_20160502_1718'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cosinnusgroupmembership',
            options={'verbose_name': 'Team membership', 'verbose_name_plural': 'Team memberships'},
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='is_active',
            field=models.BooleanField(default=True, help_text='If a team is not active, it counts as non-existent for all purposes and views on the website.', verbose_name='Is active'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='name',
            field=models.CharField(max_length=250, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='related_groups',
            field=models.ManyToManyField(related_name='_related_groups_+', to=settings.COSINNUS_GROUP_OBJECT_MODEL, through='cosinnus.RelatedGroups', blank=True, null=True, verbose_name='Related Teams'),
        ),
        migrations.AlterField(
            model_name='cosinnusgroup',
            name='type',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Project Type', editable=False, choices=[(0, 'Project'), (1, 'Group')]),
        ),
        migrations.AlterField(
            model_name='cosinnuslocation',
            name='group',
            field=models.ForeignKey(related_name='locations', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_left',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_left_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_left_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_left_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_left_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_right',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_right_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_right_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_right_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='banner_right_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content1',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content1_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content1_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content1_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content1_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content2',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content2_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content2_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content2_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='content2_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_left',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_left_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_left_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_left_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_left_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_right',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_right_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_right_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_right_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='footer_right_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='header',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='header_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='header_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='header_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboarddoublecolumnpage',
            name='header_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_left',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_left_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_left_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_left_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_left_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_right',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_right_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_right_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_right_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='banner_right_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='content1',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='content1_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='content1_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='content1_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='content1_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_left',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_left_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_left_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_left_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_left_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_right',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_right_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_right_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_right_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='footer_right_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='header',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='header_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='header_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='header_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardsinglecolumnpage',
            name='header_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_left',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_left_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_left_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_left_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_left_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_right',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_right_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_right_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_right_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='banner_right_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right banner (top)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content1',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content1_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content1_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content1_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content1_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (left column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content2',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content (center column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content2_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (center column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content2_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (center column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content2_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (center column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content2_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (center column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content3',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content3_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content3_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content3_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='content3_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content (right column)', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_left',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_left_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_left_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_left_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_left_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_right',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_right_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_right_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_right_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='footer_right_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Right footer', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='header',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='header_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='header_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='header_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamdashboardtriplecolumnpage',
            name='header_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Header', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpleonepage',
            name='content',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpleonepage',
            name='content_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpleonepage',
            name='content_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpleonepage',
            name='content_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpleonepage',
            name='content_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='content',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='content_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='content_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='content_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='content_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Content', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='leftnav',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], verbose_name='Left Sidebar', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='leftnav_de',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left Sidebar', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='leftnav_en',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left Sidebar', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='leftnav_ru',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left Sidebar', blank=True),
        ),
        migrations.AlterField(
            model_name='streamsimpletwopage',
            name='leftnav_uk',
            field=wagtail.wagtailcore.fields.StreamField([('paragraph', cosinnus.models.wagtail_blocks.BetterRichTextBlock(icon='form')), ('image', wagtail.wagtailimages.blocks.ImageChooserBlock(icon='image')), ('create_project_button', wagtail.wagtailcore.blocks.StructBlock([(b'type', wagtail.wagtailcore.blocks.ChoiceBlock(default='project', choices=[('project', 'Project'), ('group', 'Group')], label='Type'))]))], null=True, verbose_name='Left Sidebar', blank=True),
        ),
        migrations.AlterField(
            model_name='tagobject',
            name='group',
            field=models.ForeignKey(related_name='+', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, null=True),
        ),
    ]
