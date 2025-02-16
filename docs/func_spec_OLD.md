######################################################################
# MCQ Trainer V1.0 Functional Spec
######################################################################

# MCQ Trainer

MCQ Trainer helps you manage the curation of training docs to answer MCQ in any knowledge domain.

# User stories

As a user, I can:

- Configure one or more experiments comprising 
  - take-quiz input file
  - list of training docs
  - custom prompt strategies (e.g. customize CoT prompt)
- Run the experiment and view the score and the configuration.
- Recall past experiments to guide optimization of configuration.
- Use LLM-generated configuration evolution


## Roadmap

1. MVP 
   - UI: Command line 
   - Question/Answer input
     - Local file read
     - google sheet
   - RAG
     - Local file ingestion
     - Customizable embedding model (Biobert etc)
     - Fixed-size chunking (user specified)
     - Embeddings stored on disk
   - LLM Prompting
     - Multiple prompting strategies
       - Chain of Thought (encourage step-by-step reasoning)
       - Few-shot (similar examples)
       - Contrarian Analysis (challenge assumption to avoid bias)
   - Post-LLM answer refinement 
     - Confidence-based voting
       - use multiple attempts with different strategies
       - weight answers based on LLM-provided confidence scores
       - return most consistently confident answer

2. Phase 2
   - Vector database
   - Directory and S3 ingestion
   - Semantic chunking
   - UI dashboard for experiment tracking and comparison
   - Multiple embedding model options

3. Phase 3
   - Advanced search
   - Fine-tuning integration

---
