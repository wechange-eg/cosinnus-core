Coding Style
============

We use the following coding style guidelines and tools in development.

Python
------

The project contains an `.editorconfig` file defining the basic formatting as used by the Django project.

This mainly includes:

- 4 spaces for indentation
- Maximum line length of 120

We also use Ruff (https://docs.astral.sh/ruff/ ) for linting and automatic code formatting using pre-commit
hooks.

To enable ruff in the development environment run::

    pre-commit install

After this all commits are checked and formatted with Ruff.

Additionally it is advised to enable ignoring the main styling commit in `git blame`::

    git config --local blame.ignoreRevsFile .git-blame-ignore-revs

