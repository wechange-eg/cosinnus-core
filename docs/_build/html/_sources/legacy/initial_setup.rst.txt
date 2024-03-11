=============
Initial Setup
=============

Bootstrapping the database
==========================

Be sure to not create the default admin user when bootstrapping the database,
because the table for the user profile doesn't exit at that time and the
command will fail. It is recommended to run these commands:

.. sourcecode:: bash

   $ python manage.py syncdb --noinput
   $ python manage.py migrate
   $ python manage.py createsuperuser
