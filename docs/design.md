######################################################################
# Func Spec 
######################################################################

## Target user

Cost-sensitive users in low income environments / countries
wanting to train MCQ taker (e.g. starving students).

## User stories

As a user I want: 

- To easily train a MCQ test taker in any subject domain. 
- To provide sample Q & A and list of documents to train.
- To achieve max accuracy.
- To keep training costs as low as possible
- To keep training as simple and fast as possible (no complex setup; can run on my laptop)
- A clear audit trail of training experiments so I know which prompt template / strategies worked best.
- Versioned prompt templates so I don't forget what worked. 
- To deploy easily as a single docker image anywhere (Once optimally trained).

######################################################################
# Design 
######################################################################

## I want to easily train a MCQ test taker in any subject domain.
- Minimal configuration.
- Simple command line OR gui hosted on laptop (no remote servers)

## I provide sample Q & A and list of documents to train.
- Q & A to be persisted on disk as CSV.
- Each Experiment references an input Q & A file.

## I want to achieve 90% accuracy.
- RAG document search space should be subject-specific to match the domain of each question.
  This implies multiple vectordb collections keyed by subject.

## I want to keep training costs as low as possible
- Constrain to GPT 3.5 (cheaper).
- Generate RAG embeddings locally instead of calling openAI.
- No fine-tuning (expensive / unclear benefit if not trained enough; RAG may be more accurate).

## I want to keep training as simple as possible (no complex setup; can run on my laptop)
- Tilts strategy toward quality RAG and emphasizes judicious selection of training docs
  for expected questions.

## I want versioned prompt templates so I don't forget what worked. 
- Prompts should be defined in separate clearly versioned files, not mixed in code. 

## I want a clear audit trail of training experiments so I know which worked the best.
- Experiment results should be persisted.
- Experiment configuration to enumerate all variables (prompt template versions, chosen prompt strategies)

## Once optimally trained, I want be able to deploy as a docker image 
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

