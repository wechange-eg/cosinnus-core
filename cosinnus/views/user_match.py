import logging
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http.response import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

from cosinnus import cosinnus_notifications
from cosinnus.conf import settings
from cosinnus.default_settings import LOGIN_URL
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.profile import UserMatchObject, get_user_profile_model
from cosinnus.models.tagged import LikeObject
from cosinnus.utils.functions import is_number
from cosinnus.utils.permissions import check_user_can_see_user
from cosinnus.utils.user import filter_active_users
from cosinnus.views.mixins.group import RequireLoggedInMixin

logger = logging.getLogger('cosinnus')


USER_MATCH_LIKES_CACHE_KEY = 'cosinnus/core/portal/%d/user_match/likes/'
USER_MATCH_LIKES_CACHE_TIMEOUT = 60 * 5  # 5 minutes


class UserMatchListView(RequireLoggedInMixin, ListView):
    model = get_user_profile_model()
    template_name = 'cosinnus/user/user_match_list.html'
    login_url = LOGIN_URL

    def get_hashed_likes(self):
        """Returns a dict with all likes by all users. The likes are stored in a hashed string format."""
        cache_key = USER_MATCH_LIKES_CACHE_KEY % (CosinnusPortal.get_current().id)
        likes_by_user = cache.get(cache_key)
        if not likes_by_user:
            likes_by_user = {}
            values_liked = LikeObject.objects.filter(liked=True).values_list('user', 'content_type', 'object_id')
            for user, content_type, object_id in values_liked:
                if user not in likes_by_user:
                    likes_by_user[user] = set()
                likes_by_user[user].add(f'{content_type}::{object_id}')
            cache.set(cache_key, likes_by_user, USER_MATCH_LIKES_CACHE_TIMEOUT)
        return likes_by_user

    # TODO: cache after!
    def get_scored_user_profiles(self):
        # exclude self
        user_profiles = self.model.objects.exclude(user=self.request.user)

        # filter only users I haven't liked or disliked yet
        already_liked_users = UserMatchObject.objects.filter(
            from_user=self.request.user, type__in=[UserMatchObject.LIKE, UserMatchObject.DISLIKE]
        ).values_list('to_user_id', flat=True)
        user_profiles = user_profiles.exclude(user_id__in=already_liked_users)

        # prefetch related
        user_profiles = user_profiles.prefetch_related('user', 'media_tag', 'media_tag__tags')

        # filter out users that did not like me
        disliked_by_users = UserMatchObject.objects.filter(
            to_user=self.request.user, type=UserMatchObject.DISLIKE
        ).values_list('from_user_id', flat=True)
        user_profiles = user_profiles.exclude(user_id__in=disliked_by_users)

        # filter active users
        user_profiles = filter_active_users(user_profiles, filter_on_user_profile_model=True)

        # filter user to be active within the last year
        last_year = now() - timedelta(
            days=365
        )  # timedelta to pass users who have logged in at least once within the last year;
        user_profiles = user_profiles.filter(user__last_login__gte=last_year)

        # filter users for their profile visibility
        users = get_user_model().objects.filter(cosinnus_profile__in=user_profiles)
        users = users.prefetch_related('cosinnus_profile', 'cosinnus_profile__media_tag')
        checked_for_visibility_users = [user for user in users if check_user_can_see_user(self.request.user, user)]
        user_profiles = user_profiles.filter(user_id__in=checked_for_visibility_users)

        # get likes for all users to avoid queries per user.
        user_likes = self.get_hashed_likes()

        # get request user likes and tags
        request_user_likes = user_likes.get(self.request.user.id, set())
        request_user_tags = list(self.request.user.cosinnus_profile.media_tag.tags.all())

        score_dict = {}

        for profile in user_profiles:
            score = 0
            # profile fields score
            if profile.description and len(profile.description) > 10:
                score += 1
            if profile.avatar:
                score += 1
            if profile.website:
                score += 1
            if profile.email_verified:
                score += 1

            # Score dynamic fields
            if profile.dynamic_fields:
                for field, value in profile.dynamic_fields.items():
                    if value:
                        score += 1
                        user_value = self.request.user.cosinnus_profile.dynamic_fields.get(field)
                        if user_value:
                            if isinstance(value, list):
                                try:
                                    score += len(set(user_value).intersection(set(value)))
                                except TypeError:
                                    # Could not convert list to set. Just ignore the field.
                                    pass
                            elif user_value == value:
                                score += 1

            # Score topics
            if profile.media_tag.topics:
                score += 1
                user_topics = self.request.user.cosinnus_profile.media_tag.get_topics()
                score += len(set(profile.media_tag.get_topics()).intersection(set(user_topics)))

            # Score tags
            if profile.media_tag.tags.exists():
                score += 1
                score += len(set(profile.media_tag.tags.all()).intersection(set(request_user_tags)))

            # score users active in the last month
            last_month = now() - timedelta(days=31)
            if profile.user.last_login > last_month:
                score += 1

            # mutual likes score
            if request_user_likes:
                this_user_liked_set = user_likes.get(profile.user_id, set())
                set_intersection = this_user_liked_set.intersection(request_user_likes)
                shared_like_count = len(set_intersection)
                score += shared_like_count

            score_dict[profile.id] = score

        score_dict = sorted(score_dict.items(), key=lambda score: score[1], reverse=True)
        result_score = {k: v for k, v in score_dict}

        # get first 3 user profiles with the highest counted score
        selected_user_profiles = list(result_score.keys())[:3]

        # all active users related to the selected user profiles
        scored_user_profiles = list(self.model.objects.select_related('user').filter(id__in=selected_user_profiles))
        scored_user_profiles = sorted(scored_user_profiles, key=lambda p: result_score[p.id], reverse=True)

        # Include one user that liked me in the selection
        liked_by_users = UserMatchObject.objects.filter(
            to_user=self.request.user, type=UserMatchObject.LIKE
        ).values_list('from_user_id', flat=True)
        selected_include_liked = set(liked_by_users).intersection(set(selected_user_profiles))
        if not selected_include_liked:
            # Get the user that liked me with the best matching score
            liked_by_user_profiles = user_profiles.filter(user_id__in=liked_by_users).all()
            liked_by_user_profiles = sorted(liked_by_user_profiles, key=lambda p: result_score[p.id], reverse=True)
            liked_by_user_profile = liked_by_user_profiles[0] if liked_by_user_profiles else None
            if liked_by_user_profile:
                # Add the user at a random position
                scored_user_profiles = scored_user_profiles[:2]
                random.seed()
                random_pos = random.randrange(3)
                scored_user_profiles.insert(random_pos, liked_by_user_profile)
        return scored_user_profiles

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_user_id = self.request.GET.get('user')
        if selected_user_id:
            # show user specified by request parameter
            selected_user = self.model.objects.filter(user__pk=selected_user_id).first()
            scored_user_profiles = [selected_user] if selected_user else []
        else:
            # show scored user profiles
            scored_user_profiles = self.get_scored_user_profiles()

        context.update(
            {
                'scored_user_profiles': scored_user_profiles,
            }
        )

        return context


def check_for_user_match(from_user, to_user):
    """Checks if between two users, a MatchObject exists, in a way that both users
    "like" each other, and if so, triggers different effects."""

    match_case_from = UserMatchObject.objects.filter(
        from_user=from_user, to_user=to_user, type=UserMatchObject.LIKE
    ).first()
    match_case_to = UserMatchObject.objects.filter(
        from_user=to_user, to_user=from_user, type=UserMatchObject.LIKE
    ).first()

    if match_case_from and match_case_to:
        # open rocketchat
        if settings.COSINNUS_ROCKET_ENABLED:
            match_case_from.get_rocketchat_room_url()  # sets rocketchat room ids and name in the match object
            if match_case_from.rocket_chat_room_id and match_case_from.rocket_chat_room_name:
                match_case_to.rocket_chat_room_id = match_case_from.rocket_chat_room_id
                match_case_to.rocket_chat_room_name = match_case_from.rocket_chat_room_name
                match_case_to.save()

                # Create notifications
                cosinnus_notifications.user_match_established.send(
                    sender=from_user,
                    obj=match_case_from,
                    user=from_user,
                    audience=[
                        to_user,
                    ],
                )

                cosinnus_notifications.user_match_established.send(
                    sender=to_user,
                    obj=match_case_to,
                    user=to_user,
                    audience=[
                        from_user,
                    ],
                )
            else:
                logger.info('RocketChat is not enabled on this portal!')
    elif match_case_from:
        # send like notification
        cosinnus_notifications.user_match_liked.send(
            sender=from_user,
            obj=match_case_from,
            user=from_user,
            audience=[
                to_user,
            ],
        )


def match_create_view(request):
    """
    Creates an `UserMatchObject` where the `from_user` represents the current user,
    `to_user` is certain user who got 'liked' or 'disliked',
    and `action` is certain type of reaction which `to_user` got from `from_user`.

    Args:
        request

    Raises:
        ValidationError: if `user_id` from POST.data is not an integer or is None;
        ValueError: if `action` from POST.data is not 'like', 'dislike' or 'ignore' or is None;
        ObjectDoesNotExist: if UserObject does not match the one with the given id;

    Returns:
        redirect: UserMatchListView
    """
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated.')

    # check if `user_id` is a number
    user_id = request.POST.get('user_id')
    if user_id is None or not is_number(user_id):
        raise ValidationError(message=_('User id should be an integer and it should not be None.'))

    # check if `action` matches the given ones
    action = request.POST.get('action')
    if action is None or int(action) not in dict(UserMatchObject.TYPE_CHOICES).keys():
        raise ValueError('Action should be either "like", "dislike" or "ignore" and it should not be None.')

    # check if certain user exists
    user = get_user_model().objects.get(id=user_id)
    if not user or user is None:
        raise ObjectDoesNotExist('User matching query does not exist')

    # create `UserMatchObject`
    match_object, created = UserMatchObject.objects.get_or_create(
        from_user=request.user, to_user=user, defaults={'type': action}
    )
    if not created and not match_object.type == action:
        match_object.type = action
        match_object.save()

    check_for_user_match(request.user, user)

    return redirect('cosinnus:user-match')


user_match_list_view = UserMatchListView.as_view()
