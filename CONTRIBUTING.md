# Contributing

Thanks for your interest in improving Package Maximizer.

## Development setup

```bash
git clone https://github.com/dominicusin/package-maximizer.git
cd package-maximizer
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
make test
```

## Linting

```bash
flake8 package_maximizer/ tests/ --count --select=E9,F63,F7,F82
black package_maximizer/ tests/
mypy package_maximizer/
```

## Documentation

```bash
sphinx-build -b html docs docs/_build/html
```

## Pull requests

- Keep changes focused and minimal.
- Add tests for new behavior.
- Update README/docs when public behavior changes.
