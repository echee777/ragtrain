## Observations

1. We should record llm responses as part of the ExperimentResults but NOT the evaluation of the responses.
   Reason being that performance is dependent on the evaluation strategy and can be 
   refined after interrogating the LLM.
  
2. COT and Contrarian seem to get the correct answer when they agree
   - They don't always agree but when they do they can be more accurate than RAG (if the RAG is not done right)

3. There are numerous answers where *all* prompt strategies agreed on the answer but wrongly.
   - Fixing RAG bugs or training with more relevant docs is probably the way to go.
    
4. Would search results help?  Verdict: Unlikely OR Uncertain (needs further assessment)
   - I did an experiment (see manual/google.py) wherein I used SerpAPI to download the top links for Flavr Savr
   - Turns out it's actually from Biology2e.  So in theory RAG would have sufficed.
   - The problem seems to be that RAG was unable to answer "all the above" (because of a bug in the RAG
     that's causing the relevant chunk NOT to be recalled).
   - I also noticed a lot of junk text in the search results which implies a lot of cleaning. Not a good time 
     investment for uncertain benefit.
 
5. Noticed that some questions are terse.  Issuing multiple embedding queries for combinations of 
   question, question+answer[x], question+all_answers seemed rational.
   Sort all retrieved chunks by score descending and return the top k.

6. Final result: Poor performance 13/20 max but clearly RAG is not working as it should (Flavr Savr chunk
   not recalled.  Suspect that fixing the RAG bug will significantly increase score.