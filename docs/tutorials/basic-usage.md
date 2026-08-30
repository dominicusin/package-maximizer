# Basic Usage

## Installation

.. code-block:: bash

   pip install package-maximizer

## CLI

.. code-block:: bash

   pm maximize pkg1 pkg2 pkg3
   pm export pkg1 pkg2 --format graphml
   pm init-config

## Web API

Start the API server:

.. code-block:: bash

   pm-web

Then call:

.. code-block:: bash

   curl -H "X-API-Key: $PM_API_KEY" \
     -X POST http://127.0.0.1:5000/api/v1/maximize \
     -H "Content-Type: application/json" \
     -d '{"packages": ["vim", "nano"]}'
