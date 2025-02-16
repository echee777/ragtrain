# RagTrain

## Project Organization

```python
root/
├── data/              # Application data and resources
├── docs/             # Detailed documentation
├── src/              # Source code root
│   └── ragtrain/     # Main package
├── tests/            # Test suite
├── pixi.toml         # Pixi environment configuration
└── pixi.lock         # Pixi dependency lock file

## Quickstart

- install pixi on your system
- cd <root>/
- pixi install
- pixi run post-install (to install chromadb)

See docs/ for
- [functional spec & design doc](/docs/design.md)
- [development approach](/docs/development.md)