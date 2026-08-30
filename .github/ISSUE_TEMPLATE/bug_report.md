name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: dominicusin

body:
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What went wrong?
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Reproduction
      description: Steps or minimal example
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version
      description: Package Maximizer version
    validations:
      required: true
