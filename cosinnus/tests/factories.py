from typing import TypeVar

import factory
from django.contrib.auth import get_user_model

from cosinnus.models import (
    MEMBERSHIP_ADMIN,
    MEMBERSHIP_INVITED_PENDING,
    MEMBERSHIP_MANAGER,
    MEMBERSHIP_MEMBER,
    MEMBERSHIP_PENDING,
    CosinnusBaseGroup,
    CosinnusGroupMembership,
)
from cosinnus.models.group_extra import (
    CosinnusConference,
    CosinnusProject,
    CosinnusSociety,
)
from cosinnus_note.models import Note

User = get_user_model()


class ActiveUserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Sequence(lambda n: f'TestUser_{n}')
    last_name = factory.Sequence(lambda n: f'Müller_{n}')
    is_active = True
    last_login = factory.Faker('past_datetime', start_date='-1y')

    @factory.post_generation
    def verified_profile(self, create, extracted, **kwargs):
        if not create:
            return

        profile = self.cosinnus_profile
        profile.email_verified = True
        profile.tos_accepted = True

        for key, value in kwargs.items():
            setattr(profile, key, value)

        profile.save()


def add_users_with_status(group, users, status, **kwargs):
    for user in users:
        group.add_member_to_group(
            user,
            membership_status=status,
            **kwargs,
        )


TBaseGroup = TypeVar(
    'TBaseGroup',
    bound=CosinnusBaseGroup,
)


class CosinnusBaseGroupFactory(factory.django.DjangoModelFactory[TBaseGroup]):
    class Meta:
        model = CosinnusBaseGroup
        abstract = True

    name = factory.Sequence(lambda n: f'Test Group {n}')

    @factory.post_generation
    def admins(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        add_users_with_status(self, extracted, MEMBERSHIP_ADMIN, **kwargs)

    @factory.post_generation
    def managers(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        add_users_with_status(self, extracted, MEMBERSHIP_MANAGER, **kwargs)

    @factory.post_generation
    def members(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        add_users_with_status(self, extracted, MEMBERSHIP_MEMBER, **kwargs)

    @factory.post_generation
    def invited(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        add_users_with_status(self, extracted, MEMBERSHIP_INVITED_PENDING, **kwargs)

    @factory.post_generation
    def pending(self, create, extracted, **kwargs):
        if not create or not extracted:
            return

        add_users_with_status(self, extracted, MEMBERSHIP_PENDING, **kwargs)


class CosinnusProjectFactory(CosinnusBaseGroupFactory[CosinnusProject]):
    class Meta:
        model = CosinnusProject

    name = factory.Sequence(lambda n: f'Test Project {n}')


class CosinnusSocietyFactory(CosinnusBaseGroupFactory[CosinnusSociety]):
    class Meta:
        model = CosinnusSociety

    name = factory.Sequence(lambda n: f'Test Society {n}')


class CosinnusConferenceFactory(CosinnusBaseGroupFactory[CosinnusConference]):
    class Meta:
        model = CosinnusConference

    name = factory.Sequence(lambda n: f'Test Conference {n}')


class CosinnusMembershipFactory(factory.django.DjangoModelFactory[CosinnusGroupMembership]):
    class Meta:
        model = CosinnusGroupMembership

    user = factory.SubFactory(ActiveUserFactory)
    group = factory.SubFactory(CosinnusSocietyFactory)
    status = MEMBERSHIP_MEMBER


class NoteFactory(factory.django.DjangoModelFactory[Note]):
    class Meta:
        model = Note

    group = factory.SubFactory(CosinnusSocietyFactory)
    creator = factory.SubFactory(ActiveUserFactory)
    title = factory.Sequence(lambda n: f'Test Note {n}')
    text = factory.Faker('paragraph', nb_sentences=3)
