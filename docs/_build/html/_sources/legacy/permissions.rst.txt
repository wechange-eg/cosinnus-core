===========
Permissions
===========

The access to all objects that are part of the Cosinnus environment are based on
the following permission model:

* A user can be *authenticated*
* A user that is *authenticated* can be a *superuser*
* A user that is *authenticated* can be a *group member*
* A user that is a *group member* can be a *group admin* (This implies that a
  *group admin* always is a *group member* of that group)

.. warning::

   Due to a `bug in Django <https://code.djangoproject.com/ticket/6707>`_ **DO
   NOT** remove a *group member* that is still a *group admin*!

Further more:

* A group can be *public*

Additionally the access to objects is differentiated between *read* access,
*write* access and *admin* access. Read access is e.g.:

* List all objects of a certain type
* Show the details for a certain object

Write access is e.g.:

* Create an object of a certain type
* Update a certain object
* Delete a certain object

Admin access is e.g.:

* Modify group name
* Add / remove group members

Taking all those restrictions into account results in the following permission
schema:

=============  ============  ===========  =========  ======   ====  =====  =====
authenticated  group member  group admin  superuser  public   read  write  admin
=============  ============  ===========  =========  ======   ====  =====  =====
NO             x             x            x          YES      YES   NO     NO
NO             x             x            x          NO       NO    NO     NO
-------------  ------------  -----------  ---------  ------   ----  -----  -----
YES            x             x            YES        x        YES   YES    YES
YES            x             YES          NO         x        YES   YES    YES
-------------  ------------  -----------  ---------  ------   ----  -----  -----
YES            YES           NO           NO         x        YES   YES    NO
-------------  ------------  -----------  ---------  ------   ----  -----  -----
YES            NO            NO           NO         YES      YES   YES    NO
YES            NO            NO           NO         NO       NO    NO     NO
=============  ============  ===========  =========  ======   ====  =====  =====
