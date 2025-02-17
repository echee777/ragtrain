######################################################################
# Func Spec 
######################################################################

## Target user

System integrators able to perform simple customizations to optimize training.


## User stories

As a user I want: 

- To easily train a MCQ test taker in any subject domain. 
- To provide sample Q & A and list of documents to train.
- To achieve 90% accuracy.
- To keep training costs as low as possible
- To keep training as simple and fast as possible (no complex setup; can run on my laptop)
- A clear audit trail of training experiments so I know which one worked the best.
- To collaboratively edit artifacts with remote parties (e.g. prompt modifications)
- To deploy easily as a single docker image anywhere (Once optimally trained).

######################################################################
# Design 
######################################################################

## I want to easily train a MCQ test taker in any subject domain.
- Minimal inputs or configuration.
- Either easy command line commands OR gui with backend hosted on laptop.

## I provide sample Q & A and list of documents to train.
- Q & A to be persisted on disk as CSV for V1.
- Each Experiment must reference the Q & A file.

## I want to achieve 90% accuracy.
- RAG document search space should be subject specific to match the domain of a question.
  This implies multiple vector database collections keyed by subject.

## I want to keep training costs as low as possible
- Constrain to GPT 3.5 (cheaper).
- No fine-tuning (expensive / unclear benefit if not trained enough; RAG may be more accurate).
- Generate RAG embeddings locally instead of calling openAI

## I want to keep training as simple as possible (no complex setup; can run on my laptop)
- Either easy command line commands OR gui with backend hosted on laptop.
- No fine-tuning (unclear benefit if not correctly fine tuned?).
- Tilts strategy toward quality RAG, training document selection.

## I want a clear audit trail of training experiments so I know which one worked the best.
- Experiment results should be persisted
- Prompts should be in versioned text files
- Experiment configuration should enumerate all variables (prompt template version)

## I want to collaboratively edit artifacts with remote parties (e.g. prompt modifications)
- Prompts should be in their own files. 

## Once optimally trained, I want to deploy easily as a single docker image anywhere.
- Document database to be incorporated into production docker image
- All libraries (Vector database, relational databases) to be included in docker image

######################################################################
# Detailed design 
######################################################################

## Embeddings

- Embeddings should be domain-specific (e.g. Biobert for biology subject domain embeddings)
- General embedder is used if no domain-specific embedder exists. 

## Chunking

- Given 3.5's limited 16K token context, chunks have to be smaller. 
- Chunk overlap to be employed for context continuity.
- Semantic chunking is preferred to minimize fragmented retrieval, logical flow
- Semantic chunking will be limited to chunk sizes (also with chunk overlap).

