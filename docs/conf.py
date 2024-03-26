# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Initialize Django and cosinnus for autodoc
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'cosinnus.tests.settings.standalone_settings'
os.environ['WECHANGE_SECRET_KEY'] = 'dummy-secret'
os.environ['WECHANGE_DATABASE_URL'] = 'postgres://dummy:dummy@localhost/dummy'
import django
django.setup()
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
initialize_cosinnus_after_startup()



# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Cosinnus'
copyright = '2024, wechange eG'
author = 'wechange eG'

# version
import cosinnus
version = cosinnus.VERSION
release = cosinnus.VERSION


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']
exclude_patterns = ['_build', '**migrations**']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
