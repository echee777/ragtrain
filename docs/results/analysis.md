## Observations

1. We should record llm responses for a set of prompts (and number of times run)
   - Repeat evaluations of "best answer" heuristic can be run post-llm
  
2. COT and Contrarian seem to get the correct answer when they agree
   - However they don't always agree 
   - When they agree they can be more accurate than RAG; this reflects the general capability of the LLM

3. There are numerous answers were all prompt strategies agree but are wrong.
   - This is probably the use case that just needs more/better RAG training docs.
    
4. Multiple LLM concordance would help a lot but the stated constraint is only GPT3.5

5. Would search results help?  Verdict: Unlikely OR Uncertain (needs further assessment)
   - I did an experiment (see manual/google.py) wherein I used SerpAPI to download the top links for Flavr Savr
   - Turns out it's actually from Biology2e.  So in theory RAG would have sufficed.
   - The problem seems to be that RAG was unable to answer "all the above" even though Biology 2e content
     semantically indicates so.
   - I also noticed a lot of junk text in the search results which implies a lot of cleaning. Not a good time 
     investment for uncertain benefit.
 
6. Conclusion: Using Flavr Savr example, we see that the content was in RAG document set. I think we should consider
   marshalling the answers, not just the question for the RAG retrieval.  Alternately, run multiple retrievals
   with just the question, then question + each answer, then take the top scores.
