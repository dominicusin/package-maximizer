# Custom Solver Guide

Implement the ``ConstraintSolver`` interface:

.. code-block:: python

   from package_maximizer.core.interfaces import ConstraintSolver
   from package_maximizer.core.package import Package
   from typing import Iterable

   class MySolver(ConstraintSolver):
       def solve(self, packages: Iterable[Package]) -> list[str]:
           # Return a consistent set of package names.
           return []

Then register it in your code or via DI:

.. code-block:: python

   from package_maximizer.di import SolverFactory
   factory = SolverFactory()
   factory.register("my_solver", lambda: MySolver())
