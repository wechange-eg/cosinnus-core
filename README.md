wechange core codebase ("cosinnus-core")
========================================

This is the main codebase of the backend (django) and legacy frontend code of wechange, the white-label digital home for your community. For more information about wechange, see https://wechange.coop/.

### Contributing to wechange

You'd like to contribute a bug fix or feature for wechange? Great! These are the basic steps on how to do so:

1. Install a basic wechange portal for local development using the guide here: https://git.wechange.de/gl/code/template-portal
2. Make changes in the `cosinnus-core` (https://git.wechange.de/gl/code/cosinnus) repository on your local machine that you set up in Step 1.
3. Make sure you have thoroughly tested your changes and that your code quality is sufficient. Please adhere to the code styles as outlined in https://wechange.de/docs/coding_style.html and make sure to install the code-format pre-commit hooks.
4. Push your changes to a feature branch in the `cosinnus-core` repository. This branch should ideally be up-to-date with the **Bleeding-edge development branch**.
5. Submit a merge request to the cosinnus-core repository here: https://git.wechange.de/gl/code/cosinnus/-/merge_requests


### Documentation

* A written overview of the cosinnus framework architecture can be found here: https://wechange.de/docs/components.html
* An autodoc code documentation can be found here: https://wechange.de/docs/refs/modules.html


### Overview of the branches for cosinnus-core

As we are currently still working on logistical and architectural changes for the large wechange Redesign, the branch structure of this repository is in a state of changing over from the legacy state. As such, the `main` branch is not the branch for the most recent changes during this period. 

These are the notable branches at this time.

* **Current production version branch**: https://git.wechange.de/gl/code/cosinnus/-/tree/release/redesign-release-2.1?ref_type=heads
* **Next Release-candidate development branch**: https://git.wechange.de/gl/code/cosinnus/-/tree/release/test/redesign-release-2.1?ref_type=heads
* **Bleeding-edge development branch**:  https://git.wechange.de/gl/code/cosinnus/-/tree/redesign-dev?ref_type=heads
