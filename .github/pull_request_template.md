name: Pull request
about: Submit a change for review
title: ''
labels: ''
assignees: dominicusin

body:
  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: What changed and why?
    validations:
      required: true
  - type: textarea
    id: checks
    attributes:
      label: Checks
      description: Confirm local verification
      value: |
        - [ ] make test passes
        - [ ] flake8 critical check passes
        - [ ] docs updated if behavior changed
    validations:
      required: true
