Development Setup
=================

This document describes the setup steps required to be able to develop on the Cosinnus-Core Project.
As Cosinnus is not a standalone project a portal setup is also needed.

This will set up a local development environment, getting you ready to work on a Cosinnus portal and all its internal apps.

Here we describe the setup based on the `wechange` portal, but the steps also work with other existing portals or when
creating a new portal based on the `template-portal`.

Prerequisites
-------------

Please install the following dependencies:

- postgresql
- git
- pip

Create PostgreSQL database
--------------------------

Create new database in PostgreSQL shell::

    CREATE USER <DB-USER> WITH PASSWORD '<DB-PASSWORD>';
    CREATE DATABASE <DB-NAME> WITH OWNER <DB-USER>;

Install Python, pip and poetry
------------------------------

- Install these system libraries::

    apt install binutils libproj-dev gdal-bin

-  For Ubuntu you will also need these system libraries::

    apt install libjpeg-dev zlib1g-dev libffi-dev libpq-dev python3-dev zlib1g-dev

-  For MacOS you will also need to install the development libraries for `zlib`::

    xcode-select –install

-  Install pyenv:

   -  See: https://github.com/pyenv/pyenv
   -  Install package if available e.g.::

        apt install pyenv

   -  Or install using pyenv-installer (https://github.com/pyenv/pyenv-installer):

      -  Run::

            curl https://pyenv.run | bash

      -  Add the following lines to `.bashrc` (for bash)::

            export PYENV_ROOT="$HOME/.pyenv"
            command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
            eval "$(pyenv init -)"

-  Install Python 3.8.10 and poetry (for dependency management)::

    pyenv install 3.8.10
    pyenv local 3.8.10
    pip install --upgrade pip
    pip install poetry

Get wechange and cosinnus source code
-------------------------------------

This will create two separate folders::

   -/Sites
   ├── wechange/ (for base project)
   ├── cosinnus/ (for wechange apps, used as a package)

-  Change to your local development folder: e. g. `cd -/Sites` or similar
-  Clone wechange::

        git clone -b redesign git@git.wechange.de:code/portals/wechange.git wechange

-  Clone cosinnus::

    git clone -b redesign git@github.com:wechange-eg/cosinnus-core.git cosinnus-core

-  Change your cosinnus branch to `main-redesign`::

    cd cosinnus-core && git checkout main-redesign && cd ..

-  Link the repos: Change the `cosinnus` dependency in `wechange/pyproject.toml` to::

    cosinnus = { path = "../cosinnus-core", develop = true }

Install all dependencies
------------------------

-  Create virtualenv and install dependencies::

    cd wechange
    poetry install (may take a couple of minutes for the first run)

-  Activate virtualenv::

    poetry shell

Troubleshooting Tips
--------------------

Help for specific issues on MacOS

1. Installing of the `zlib1g-dev` package on macOS (important in
   connection with `Pillow` package installation):

   -  install the ‘zlib’ package via brew::

        brew install zlib

   -  add the following line to your .zshrc / .bashrc file::

        export CPATH=xcrun --show-sdk-path/usr/include

   -  close and re-open your terminal window - and now you should be all
      set!

2. A problem may occur with the `reportlab` package on Apple Silicon
   devices with macOS BigSur and above as well as Python 3.8. and above
   installed.

   -  The solution would be force pip to build `reportlab` package
      within the poetry project again and install it again using this
      command::

        poetry run pip install reportlab --force-reinstall --no-cache-dir --global-option=build_ext

3. In case the `numpy` package installs with an error, try to update it to version `1.22.4`, which should work fine.


Configure settings
------------------

- Create `.env` file::

    cd wechange
    cp env.example .env

-  Edit `.env`::

    WECHANGE_DEBUG=true
    WECHANGE_DJANGO_SETTINGS_MODULE=config.settings.dev
    WECHANGE_DATABASE_URL=postgres://<DB-USER>:<DB-PASSWORD>@localhost/<DB-NAME>

One-time staticfiles installation
---------------------------------

::

    cd cosinnus-core/
    npm install
    cd cosinnus-core/cosinnus_conference/frontend/
    npm install`

You will only need to do this once, unless you change any npm packages.

One-time Django setup
---------------------

-  Create database tables::

    ./manage.py migrate

-  Create an admin user::

    ./manage.py createsuperuser

   -  enter the credentials for your local user
   -  the username doesn’t matter, you will log in using the email as credential

-  Run server::

    ./manage.py runserver

-  It works!

First-Time wechange Setup
-------------------------

-  Navigate to http://localhost:8000/admin and log in with the email address and password you just created

-  Navigate to http://localhost:8000/admin/sites/site/1/ and change the default Site to:

    -  domain: `localhost:8000`
    -  name: `Local Site` (or anything you wish)

-  Navigate to http://localhost:8000/admin/auth/user/

    -  Select your admin user
    -  Set `Email verified` setting

- Navigate to http://localhost:8000/admin/cosinnus/cosinnussociety/add/ to add the Forum Group:

    - Set Name to "Forum" (might differ for portals, see the `NEWW_FORUM_GROUP_SLUG` setting)
    - Change `Application Method` to `Everyone may join`
    - Save the group

-  Restart the server using “ctrl+c” and `./manage.py runserver`

Check if you’re up-and-running
------------------------------

- Check the following URLs:
    - http://localhost:8000/dashboard/
    - http://localhost:8000/group/forum/
- If both sites work and you have a "Forum" link in yor navigation bar, you’re all set!

(optional) Build the pre-built staticfile bundles (JS)
------------------------------------------------------

You only need to do this whenever you make any changes in the conference
frontend or map frontend.

- from your wechange-directory, run::

   ../cosinnus-core/scripts/compile-bundles.sh


- this builds `cosinnus-core/cosinnus/static/js/client.js` and `cosinnus-core/cosinnus_conference/static/conference/main.js`

(optional) Install ElasticSearch
--------------------------------

Version 7.17.9 is required and can be install with Docker. We have created docker-compose file for this.

Follow the README instructions in https://github.com/wechange-eg/cosinnus-devops/tree/master/elasticsearch-7.17.9-docker.

Configure ElasticSearch in the portal `.env` file::

    WECHANGE_HAYSTACK_URL=http://127.0.0.1:9200/
    WECHANGE_HAYSTACK_INDEX_NAME=wechange

Build the index::

    ./manage.py rebuild_index

When this works you can navigate to http://localhost:8000/map/ and see the search results.


(optional) Install Memcached
----------------------------

To use caching locally you need to install and configure the memcached service. E.g. install the Ubuntu package::

    sudo apt install memcached

Enable memedached in the portal `.env` file::

    WECHANGE_MEMCACHED_LOCATION=127.0.0.1:11211
