# Developer Guide

## Project history (initial development)

Prioritize AI-assisted development to deal with the details.  

We used Claude for the initial round.
We focussed on guiding the AI to achieve the right balance of extensibility / maintainability vs development speed. 

Given the company is gearing to scale up, we need to start minimizing siloed knowledge and start focusing on self-
explanatory code that can be easily augmented.  Given this is a committed project (not a prototype), we invest the time
to organize the code for extensibility.

## Data

Located in `/data`

These source-controlled data are examples of customer data that will be used for testing.   

They include:
- prompt templates
- questions (benchmarks)
- training docs


## Code

Located in `/src`

`src/ragtrain` is the top-level package

`src/ragtrain/embeddings`: More complex areas should get their own submodules (e.g. `ragtrain.embeddings`) and have 
the main symbols published at the package level (exported in `ragtrain.embeddings.__init__`)

### Separation of Concerns

Abstractions are introduced to support extensibility and maintainability.  

We introduce abstractions but keep the interfaces simple / lightweight to balance extensibility vs unnecessary friction. 

We also introduce intermediate manager classes.

Examples:
- TemplateManager handles loading of auditable prompt templates (by subject, version)
- PromptManager instantiates prompts and replaces variables
- HipAgent invokes GPT3.5 with prompts and evaluates best answer depending on chosen strategy
- VectorStore abstracts the vector db
- DocumentStore abstraction allows documents to be stored on disk or later in s3 etc.

Well-separated concerns should be easy to unit test. 

### Explicit enums

Fundamental constructs are explicitly enumerated to minimize mistakes throughout the codebase.

Examples:
- SubjectDomain ('biology', 'physics') are used as keys for Vector db selection and Prompt Template selection.
  Given the need to auto-fallback to 'general', we must minimize typos to void inadvertent fallback.

## Testing

Located in `/test` and `/pytest.ini`

- All functionality should be unit tested.  Hard-to-test features indicate poor separation of concerns or abstractions.
- All docker images should be goss-tested
- Integration tests and manual tests should be maintained and documented. 

## Dependency management

Located in `/pixi.toml`

Given the ML space, Conda packages are needed.  At the same time, some packages are only available on pip/pypi. 
To circumvent the issue of disjoint dependency search spaces between Conda and Pip, we use pixi.  

Pixi is fast (written in Rust).  But crucially, pixi unifies the dependency resolution space between Conda and Pip.

## Deploy

Located in `/docker`

Given the multicloud / k8s general forward strategy, all repos should have well-maintained buildfiles & Makefiles
to support docker creation.
