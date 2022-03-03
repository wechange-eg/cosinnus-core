# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import datetime
import six

from collections import defaultdict

from django.db import models
from django.utils.encoding import force_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from cosinnus_marketplace.conf import settings
from cosinnus.models import BaseTaggableObjectModel
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_marketplace import cosinnus_notifications
from django.contrib.auth import get_user_model
from cosinnus.utils.files import _get_avatar_filename

from phonenumber_field.modelfields import PhoneNumberField
from cosinnus.utils.lanugages import MultiLanguageFieldMagicMixin
from cosinnus.models.tagged import CosinnusBaseCategory, LikeableObjectMixin
from cosinnus_marketplace.managers import OfferManager
from uuid import uuid1


def get_marketplace_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'images', 'offers')


class OfferCategoryGroup(MultiLanguageFieldMagicMixin, CosinnusBaseCategory):
    
    class Meta(object):
        ordering = ['order_key']
    
    order_key = models.CharField(_('Order Key'), max_length=30, blank=True, 
         help_text='Not shown. Category groups will be sorted in alphanumerical order for this key.')


class OfferCategory(MultiLanguageFieldMagicMixin, CosinnusBaseCategory):
    
    category_group = models.ForeignKey(OfferCategoryGroup, related_name='categories', null=True, blank=True, on_delete=models.CASCADE)
    

@six.python_2_unicode_compatible
class Offer(LikeableObjectMixin, BaseTaggableObjectModel):

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
    ]

    TYPE_BUYING = 1
    TYPE_SELLING = 2

    TYPE_CHOICES = (
        (TYPE_BUYING, _('Looking for')),
        (TYPE_SELLING, _('Offering')),
    )

    type = models.PositiveIntegerField(
        _('Type'),
        choices=TYPE_CHOICES,
        default=TYPE_BUYING,
    )
    
    is_active = models.BooleanField(_('Offer currently active?'), default=True)
    
    description = models.TextField(_('Description'), blank=True, null=True)
    phone_number = PhoneNumberField(blank=True)
    
    categories = models.ManyToManyField(OfferCategory, verbose_name=_('Offer Category'), 
        related_name='offers', blank=True)
    

    objects = OfferManager()
    
    timeline_template = 'cosinnus_marketplace/v2/dashboard/timeline_item.html'

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['-created']
        verbose_name = _('Offer')
        verbose_name_plural = _('Offers')
        
    def __init__(self, *args, **kwargs):
        super(Offer, self).__init__(*args, **kwargs)

    def __str__(self):
        if self.type == self.TYPE_BUYING:
            type_verbose = 'buying'
        else:
            type_verbose = 'selling'
        readable = _('Offer: %(offer)s (%(type)s)') % {'offer': self.title, 'type': type_verbose}
        return readable
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-exchange-alt'
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Offer, self).save(*args, **kwargs)

        if created and self.is_active:
            session_id = uuid1().int
            group_followers_except_creator_ids = [pk for pk in self.group.get_followed_user_ids() if not pk in [self.creator_id]]
            group_followers_except_creator = get_user_model().objects.filter(id__in=group_followers_except_creator_ids)
            cosinnus_notifications.followed_group_offer_created.send(sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id)
            cosinnus_notifications.offer_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk), session_id=session_id, end_session=True)

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:marketplace:detail', kwargs=kwargs)
    
    def get_edit_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:marketplace:edit', kwargs=kwargs)
    
    def get_delete_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:marketplace:delete', kwargs=kwargs)

    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current offers """
        qs = Offer.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return current_offer_filter(qs)
    
    @property
    def has_expired(self):
        return self.is_active == False and self.created < now() - datetime.timedelta(days=settings.COSINNUS_MARKETPLACE_OFFER_ACTIVITY_DURATION_DAYS)
    
    @property
    def expires_on(self):
        return self.created + datetime.timedelta(days=settings.COSINNUS_MARKETPLACE_OFFER_ACTIVITY_DURATION_DAYS)
    
    def do_expire_this(self):
        # call this to make this offer expired. usually called only from cron
        self.is_active = False
        self.save(update_fields=['is_active'])
        # send signal for expiry
        cosinnus_notifications.offer_expired.send(sender=self, user=self.creator, obj=self, audience=[self.creator])
    
    def get_categories_grouped(self):
        return get_categories_grouped(OfferCategory.objects.all())
    
    def get_comment_post_url(self):
        return group_aware_reverse('cosinnus:marketplace:comment', kwargs={'group': self.group, 'offer_slug': self.slug})
    

@six.python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='marketplace_comments')
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    offer = models.ForeignKey(Offer, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(_('Text'))

    class Meta(object):
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(offer)s” by %(creator)s' % {
            'offer': self.offer.title,
            'creator': self.creator.get_full_name(),
        }
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-comment'
    
    @property
    def parent(self):
        """ Returns the parent object of this comment """
        return self.offer
    
    def get_notification_hash_id(self):
        """ Overrides the item hashing for notification alert hashing, so that
            he parent item is considered as "the same" item, instead of this comment """
        return self.parent.id

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.offer.get_absolute_url(), self.pk)
        return self.offer.get_absolute_url()
    
    def get_edit_url(self):
        return group_aware_reverse('cosinnus:marketplace:comment-update', kwargs={'group': self.offer.group, 'pk': self.pk})

    def get_delete_url(self):
        return group_aware_reverse('cosinnus:marketplace:comment-delete', kwargs={'group': self.offer.group, 'pk': self.pk})
    
    def is_user_following(self, user):
        """ Delegates to parent object """
        return self.offer.is_user_following(user)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        if created:
            session_id = uuid1().int
            # comment was created, message offer creator
            if not self.offer.creator == self.creator:
                cosinnus_notifications.offer_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.offer.creator], session_id=session_id)
            
            # message all followers of the offer
            followers_except_creator = [pk for pk in self.offer.get_followed_user_ids() if not pk in [self.creator_id, self.offer.creator_id]]
            cosinnus_notifications.following_offer_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=followers_except_creator), session_id=session_id)
            
            # message all taggees (except comment creator)
            if self.offer.media_tag and self.offer.media_tag.persons:
                tagged_users_without_self = self.offer.media_tag.persons.exclude(id=self.creator.id)
                if len(tagged_users_without_self) > 0:
                    cosinnus_notifications.tagged_offer_comment_posted.send(sender=self, user=self.creator, obj=self, audience=list(tagged_users_without_self), session_id=session_id)
            
            # end notification session
            cosinnus_notifications.tagged_offer_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[], session_id=session_id, end_session=True)
        
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.offer.group

    def grant_extra_read_permissions(self, user):
        """ Comments inherit their visibility from their commented on parent """
        return check_object_read_access(self.offer, user)


def current_offer_filter(queryset):
    """ Filters a queryset of offers for active offers. """
    return queryset.filter(is_active=True).order_by('-created')

def get_categories_grouped(category_qs):
    """ Returns a list of tuples of the categories in this filter, grouped by categorygroup name.
        All categories not assigned a group fall in the category ``zzz_misc``
    
        [('group1', [cat1, cat2]), ('group2', cat3), ... , ('zzz_misc', cat99) ] """
    
    misc_label = 'zzz_misc'
    def cat_group_key_or_misc(cat, key):
        return cat.category_group and cat.category_group[key] or force_text(misc_label)
    
    grouped_dict = defaultdict(list)
    for category in category_qs:
        if not category.category_group:
            order_key = force_text(misc_label)
        elif category.category_group.order_key:
            order_key = category.category_group.order_key
        else:
            order_key = category.category_group['name']
        grouped_dict[order_key].append(category)
    category_groups = [(cat_group_key_or_misc(grouped_dict[order_key][0], 'name'), grouped_dict[order_key]) for order_key in sorted(grouped_dict, key=lambda cat_key: cat_key.lower())]
    
    return category_groups


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_marketplace import cosinnus_app
    cosinnus_app.register()
