# RagTrain

## Project Organization

```python
<repo root>/
├── data/             # Example application data (for testing)
├── docs/             # Documentation
├── src/              # Source code root
│   └── ragtrain/     # Main package
├── tests/            # Test suite
├── pytest.ini/       # Unit test config
├── pixi.toml         # Pixi environment configuration
└── pixi.lock         # Pixi dependency lock file

## Quickstart

- install pixi on your system
- `cd <repo root>/`
- `pixi install`
- `pixi run post-install` (to install chromadb)

See docs/ for
- [functional spec & design doc](/docs/design.md)
- [development approach](/docs/development.md)