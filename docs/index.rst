Package Maximizer Documentation
===============================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api-reference
   tutorials/basic-usage
   tutorials/advanced-solvers
   guides/custom-solver

Package Maximizer
-----------------

**Package Maximizer** is a modular system for maximizing a consistent set of
packages across multiple package managers (APT, Pacman, DNF, Brew, Snap,
Flatpak, Cargo, npm).

Features
~~~~~~~~

- Multiple solver backends (Greedy, Enhanced Greedy, Z3, PuLP, OR-Tools,
  MaxSAT, MiniSAT)
- Multi-manager parser support
- Flask REST API with API-key auth
- Configurable via JSON/YAML + environment variables
- Export to JSON, CSV, and GraphML

Quick start
~~~~~~~~~~~

.. code-block:: bash

   pip install -e ".[dev,web]"
   pm init-config
   pm maximize vim nano emacs

Links
~~~~~

- Repository: https://github.com/dominicusin/package-maximizer
- Documentation: https://package-maximizer.readthedocs.io
- Issue tracker: https://github.com/dominicusin/package-maximizer/issues

Indices and tables
~~~~~~~~~~~~~~~~~~

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`
