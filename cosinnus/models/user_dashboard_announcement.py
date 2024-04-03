# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.mixins.images import ThumbnailableImageMixin
from cosinnus.utils.files import get_user_dashboard_announcement_image_filename
from cosinnus.utils.functions import unique_aware_slugify
from cosinnus.utils.urls import get_domain_for_portal
from cosinnus.views.ui_prefs import get_ui_prefs_for_user, \
    UI_PREF_DASHBOARD_HIDDEN_ANNOUNCEMENTS
from django.utils.timezone import now
from cosinnus.templatetags.cosinnus_tags import full_name


logger = logging.getLogger('cosinnus')


class UserDashboardAnnouncement(ThumbnailableImageMixin, models.Model):
    """ A sticky-type post shown seperately on top of the user-dashboard for all users.
        Can be hidden by each user with a "don't show this again" button.
        Created by portal admins in the portal administration backend area. """
        
    TYPE_EDITOR = 0
    TYPE_RAW_HTML = 1
    ANNOUNCEMENT_TYPES= (
        (TYPE_EDITOR, _('Text Editor')),
        (TYPE_RAW_HTML, _('Raw HTML')),
    )
    
    ANNOUNCEMENT_CATEGORIES = (
        (0, _('(none displayed)')),
        (1, _('Announcement')),
        (2, _('Maintenance')),
        (3, _('Update')),
        (4, _('Technical Issues')),
        (5, _('Miscellaneous')),
    )
    
    image_attr_name = 'image'
    
    class Meta(object):
        ordering = ('-valid_from',)
        unique_together = ('slug', 'portal', )
    
    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Portal'), related_name='+', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    is_active = models.BooleanField(_('Is active'),
        help_text='If an idea is not active, it counts as non-existent for all purposes and views on the website.',
        default=False)
    type = models.PositiveSmallIntegerField(_('Announcement Display Type'), blank=False,
        default=TYPE_EDITOR, choices=ANNOUNCEMENT_TYPES,
        help_text='Whether the announcement displays markdown text from an editor field or raw pasted HTML.')
    
    valid_from = models.DateTimeField(verbose_name=_('Valid From'), null=False, blank=False,
        help_text='The announcement will not be shown before this date.')
    valid_till = models.DateTimeField(verbose_name=_('Valid From'), null=False, blank=False,
        help_text='The announcement will not be shown after this date.')
    
    title = models.CharField(_('Title'), max_length=250, 
        help_text='Internal title field only.')
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    category = models.PositiveSmallIntegerField(_('Announcement Category'), blank=False,
        default=0, choices=ANNOUNCEMENT_CATEGORIES,
        help_text='A selection of text headlines to display as header')
    text = models.TextField(verbose_name=_('Text'),
         help_text=_('Main text of this announcement.'), blank=True)
    raw_html = models.TextField(verbose_name=_('Raw HTML'),
         help_text=_('Raw HTML for this announcement.'), blank=True)
    
    image = models.ImageField(_("Image"), 
        help_text='Shown as large banner image',
        null=True, blank=True,
        upload_to=get_user_dashboard_announcement_image_filename,
        max_length=250)
    
    url = models.URLField(_('URL'), blank=True, null=True,
        help_text='For the "read more" button')
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.CASCADE,
        null=True,
        related_name='+')
    last_modified = models.DateTimeField(
        verbose_name=_('Last modified'),
        editable=False,
        auto_now=True)
    
    def __str__(self):
        return 'UserDashboardAnnouncement "%s" (Portal %d)' % (self.slug, self.portal_id)

    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        current_portal = self.portal or CosinnusPortal.get_current()
        unique_aware_slugify(self, 'title', 'slug', portal_id=current_portal)
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        # set portal to current
        if created and not self.portal:
            self.portal = CosinnusPortal.get_current()
        super(UserDashboardAnnouncement, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('cosinnus:user-dashboard-announcement-edit', kwargs={'slug': self.slug})
    
    def get_edit_url(self):
        return reverse('cosinnus:user-dashboard-announcement-edit', kwargs={'slug': self.slug})
    
    def get_delete_url(self):
        return reverse('cosinnus:user-dashboard-announcement-delete', kwargs={'slug': self.slug})
    
    def get_activate_url(self):
        return reverse('cosinnus:user-dashboard-announcement-activate', kwargs={'slug': self.slug})
    
    def get_preview_url(self):
        return get_domain_for_portal(self.portal) + reverse('cosinnus:user-dashboard') + '?show_announcement=%d' % self.id
    
    def is_valid(self):
        """ Returns true if the announcement is in between its valid dates, so would be displayed """
        right_now = now()
        return bool(self.valid_from <= right_now and right_now <= self.valid_till)
    
    @property
    def category_text(self):
        return dict(self.ANNOUNCEMENT_CATEGORIES)[self.category]
    
    @classmethod
    def get_next_for_user(cls, user):
        """ Returns the next valid announcement for a user that they haven't hidden already,
            or None. """
        user_hidden_ids = get_hidden_user_dashboard_announcements_for_user(user)
        right_now = now()
        candidates = cls.objects.filter(
            portal=CosinnusPortal.get_current(),
            is_active=True,
            valid_from__lte=right_now,
            valid_till__gte=right_now,
        ).exclude(
            id__in=user_hidden_ids
        ).order_by('valid_from')
        
        if len(candidates) > 0:
            return candidates[0]
        return None
        

def get_hidden_user_dashboard_announcements_for_user(user):
    """ Returns a list of ids of UserDashboardAnnouncement that the user has chosen to 
        "not show this again". """
    if not user.is_authenticated:
        return []
    ui_prefs = get_ui_prefs_for_user(user)
    return ui_prefs[UI_PREF_DASHBOARD_HIDDEN_ANNOUNCEMENTS]
