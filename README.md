# RagTrain

## Project Organization

```
<repo root>/
├── data/             # Example application data (for testing)
├── docs/             # Documentation
├── src/              # Source code root
│   └── ragtrain/     # Main package
├── tests/            # Test suite
├── pytest.ini/       # Unit test config
├── pixi.toml         # Pixi environment configuration
└── pixi.lock         # Pixi dependency lock file
```

## Docs

See docs/ for
- [functional spec & design doc](/docs/design.md)
- [development approach](/docs/development.md)

## Quickstart

The original starter files have been moved to more rational directories.

We provide make targets so you can run tests w/o having to remember where 
various files are organized.  See `Makefile` for full description.

First install pixi (really fast; resolves Conda and pip dependencies as a unified search space)

1. Run `make setup` will run pixi to create your env then `pixi shell` to activate it.

2. `make test` to run unit tests.

3. `make pretrain` to train (chunk and embed) the provided Biology 2E text

4. `make testbench` To run the original unmodified `testbench.py`.  
   [Note that you must first set `OPENAI_API_KEY` in the environment.]  


## Running unit tests

`make test` runs the entire suite

Add a specific test name into `<repo>/pytest.ini` to run just one test.
