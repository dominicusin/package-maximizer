# Advanced Solvers

## Solver selection

- ``greedy`` — fast baseline
- ``enhanced_greedy`` — greedy with version selection
- ``z3`` — SMT via Z3
- ``pulp`` — ILP via PuLP
- ``ortools`` — CP-SAT via Google OR-Tools
- ``maxsat`` / ``minisat`` — SAT-based

## Configuration

.. code-block:: json

   {
     "default_solver": "z3",
     "default_manager": "apt",
     "cache_enabled": true
   }

## Weights

Pass weights to prefer some packages:

.. code-block:: bash

   pm maximize vim nano -w vim,2.0 -w nano,1.0
