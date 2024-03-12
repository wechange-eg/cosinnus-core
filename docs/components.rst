Key Components
==============

This part of the documentation covers the key components of Cosinnus.

*Note: Most Cosinnus models were defined as swappable models, though this feature is not used so far in the current
portals.*

Portal
------

Cosinnus is designed as a whitelabel solution. It provides all the required apps and functionality to run a portal.

A blank whitelabel portal is defined in the `template-portal` (https://git.wechange.de/code/portals/template-portal)
repository that can be branched to create a new portal.

The portal configuration is split between the portal configuration settings in the portal folder
(e.g. `wechange/config/`) and fields of the `CosinnusPortal` model, that can be adjusted via the
admin.

Many CosinnusModels depend on the Portal model. An initial `Portal` is automatically created with the migrations and can
be accessed with:

.. autofunction:: cosinnus.models.group.CosinnusPortal.get_current

Groups
------

Collaboration of a group of users is a key feature of Cosinnus. A group provides a combination of apps (i.e. News, Pads,
Events, TODOs, ...) for its members. It offers means to manage memberships and with the group-dashboard the main entry
point for collaboration.

The implementation of groups is done through the abstract base model:

.. autoclass:: cosinnus.models.group.CosinnusBaseGroup

The implementation of the abstract model is done by:

.. autoclass:: cosinnus.models.group.CosinnusGroup

There are multiple group types available implemented through proxy models:

.. autoclass:: cosinnus.models.group_extra.CosinnusProject
.. autoclass:: cosinnus.models.group_extra.CosinnusSociety
.. autoclass:: cosinnus.models.group_extra.CosinnusConference

As the group model is implemented as swappable to get the group model in your code use:

.. autofunction:: cosinnus.utils.group.get_cosinnus_group_model

Membership
----------

To participate in a group a user has to be a member of a group. The group membership is implemented via:

.. autoclass:: cosinnus.models.group.CosinnusGroupMembership

The following membership types are available:

.. autodata:: cosinnus.models.membership.MEMBERSHIP_PENDING
.. autodata:: cosinnus.models.membership.MEMBERSHIP_MEMBER
.. autodata:: cosinnus.models.membership.MEMBERSHIP_ADMIN
.. autodata:: cosinnus.models.membership.MEMBERSHIP_INVITED_PENDING
.. autodata:: cosinnus.models.membership.MEMBERSHIP_MANAGER

Depending on the `membership_mode` setting of a group there are different membership application flows:

.. autoattribute:: cosinnus.models.group.CosinnusBaseGroup.MEMBERSHIP_MODE_REQUEST
.. autoattribute:: cosinnus.models.group.CosinnusBaseGroup.MEMBERSHIP_MODE_APPLICATION
.. autoattribute:: cosinnus.models.group.CosinnusBaseGroup.MEMBERSHIP_MODE_AUTOJOIN

User Profile and Dynamic Fields
-------------------------------

Information about a user as well as user specific settings are stored in the profile model:

.. autoclass:: cosinnus.models.profile.UserProfile

Some of the basic information about the user is stored in dedicated profile fields, e.g. `avatar`,  `email_verified`,
`language`. Settings for the UI and other user preferences are stored as JSON in the `settings` field, including
`tos_accepted_date`, `newsletter_opt_in` or service IDs.

For portal specific user information the `dynamic_fields` JSON field is used. These fields are defined per portal via
the `COSINNUS_USERPROFILE_EXTRA_FIELDS` setting.

BaseTaggableObject
------------------

Cosinnus provides a way to store generic information for arbitrary models. This is done via the abstract model:

.. autoclass:: cosinnus.models.tagged.BaseTaggableObjectModel

E.g. the group model and the profile model both implement this base class. The tag model information that is referenced
by the `media_tag` field is:

.. autoclass:: cosinnus.models.tagged.BaseTagObject

This tag model includes information such as `location` and `topics`. It also includes the visibility information for
a Cosinnus model instance:

.. autoattribute:: cosinnus.models.tagged.BaseTagObject.VISIBILITY_USER
.. autoattribute:: cosinnus.models.tagged.BaseTagObject.VISIBILITY_GROUP
.. autoattribute:: cosinnus.models.tagged.BaseTagObject.VISIBILITY_ALL

Cosinnus Apps
-------------

Cosinnus provides various apps for collaboration in a group. The available apps can be selected when creating or editing
a group.

Cosinnus Cloud
""""""""""""""

Adds integration with NextCloud. A NextCloud folder is automatically created for a group and can be accessed by the
group members:

.. autoclass:: cosinnus_cloud.models.CloudFile

Cosinnus Etherpad
"""""""""""""""""

Adds integration with Etherpad/Ethercalc. Group members can collaborate on pads:

.. autoclass:: cosinnus_etherpad.models.Etherpad

Cosinnus Event
""""""""""""""

Allows to create events in a calendar or do event polls to find a data:

.. autoclass:: cosinnus_event.models.Event

Cosinnus File
"""""""""""""

A simple file sharing apps:

.. autoclass:: cosinnus_file.models.FileEntry

Cosinnus Marketplace
""""""""""""""""""""

Allows to share offers and requests between the users of a group:

.. autoclass:: cosinnus_marketplace.models.Offer


Cosinnus Message
""""""""""""""""

Provides means for chats between the users. If the RocketChat service is configured it is integrated with the group.

Cosinnus Note
"""""""""""""

Allow to post news in a group:

.. autoclass:: cosinnus_note.models.Note


Cosinnus Poll
"""""""""""""

This app allows users to use polls within a group:

.. autoclass:: cosinnus_poll.models.Poll

Cosinnus Todo
"""""""""""""

Add TODOs or TODO lists that can be assigned to users and marked as done:

.. autoclass:: cosinnus_todo.models.TodoEntry
