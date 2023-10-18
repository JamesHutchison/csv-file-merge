# CSV File Merge
This is a proof-of-concept CSV file merge operation. 

# About
This was given to me as technical homework so the design and behavior decisions are a reflection of the requirements and trying to cap the time spent.

# Some Areas of Improvement
- UX could be improved. Error handling is mostly non-existent here.
- This writes the table to the UI but file download would be more realistic
- The LLM writes code to do the column transformation, but it would be better to provide target formats and then it is just identifying the format that the input data is and the format the output data is. Having it write code was a requirement of this assignment. In general we don't want the server executing client submitted code, and likewise the LLM is inclined to write simple transformation logic and wouldn't write things to handle edge case (like cents in money when only integer values are given as examples).
- The sections that use GPT-4 are not parallelized. They could be.
- Documentation is sparse and could be improved.
- UI code is disjoint and improving is highly recommended if I were to spend more time on this.
- Unit tests.
- Full integration tests.
- Better decoupling of the UI with the underlying logic. Currently the UI is gluing things together.
- More... not a complete list

# Edge Cases
- Invalid input files or different CSV formats
   - Not really a LLM problem but of course we would want to give a friendly error if someone uploads the wrong file
   - Not uncommon for things like database dumps to be missing the header, but tab delimited, have different escape mechanisms, etc
   - Probably best handled by a dedicated library which most likely exists.
   - Could validate file prior to doing processing to ensure it's not cut off or anything, or there aren't rows with fewer columns or extra columns
- Large files
   - This solution is clearly just for demonstration purposes. While the code could probably handle large files within the limits of streamlit's file uploader,
     displaying those on the UI would likely create issues due to the number of DOM elements.
   - Already reads line by line, if it was reading from disk instead of upload
   - Already limits sample rows
- Large number of columns
   - Currently merges all columns in a single context, so this would create issues due to context length limits
   - Can mitigate issue by using model with larger context. Unlikely to have a CSV document with tons and tons of columns that's not there due to error.
   - Can apply divide and conquer (possibly map-reduce) approach if per-column logic gets too large to handle a reasonable number of columns.
- Large data cells, binary blobs, walls of text, etc
   - Similar to large number of columns, having large data cells would cause issues. This current approach includes sample values and include them would overwhelm the context.
   - Could mitigate issue by stripping data out or using something like a "<binary data>" or "<text blob>" placeholder.
   - If really needed to, could process cell individually and summarize its structure
- Scrambled column names
   - I've seen this before. Someone has a CSV with no header so they go add it themself and they mess up one or more column locations. This creates issues if the data types of the mixed up columns are the same.
   - Could look at heuristics of data and determine if there's risk data profile doesn't match and raise an alert if there is.
   - Under the current solution, the user is inclined to pick the correct column name, but if the input file has them mixed up, they'll actually pick the wrong column
   - Could help illimunate this issue by displaying example data comparisons to the user (not done in current solution)
 
# Adding learning for the transformation logic
- One way to improve the transformation logic is to add examples for the language model to refer to.
   - Increases the token usage so it increases the risks of stressing the context limit and adds to costs, but should generally be pretty minimal for this kind of data shape.
   - When the user corrects the AI by providing their own transformation logic, the AI could refer to it by example. The column information would be provided and then the user's transformation.
   - This could be stored in a SQL database or search engine. A SQL database is likely available and easy to recall examples by column name and by other heuristics such as type.
     - A document search engine would be slightly more robust because it could provide ranked examples by how well they fit.
     - A vector search engine could also be used but is likely overkill for this use case and may even be a bad tool to use here. I don't see an obvious natural language, image search, or other AI component to recalling examples from column name and shape.
- Another option is to record the data examples and then train the base model.
   - This is better fit for when there's a lot of output possibilities and some clear patterns that the AI model is missing.
   - At this time I don't see reason to think this is good approach. Adding examples to the AI prompt is portable and cheap to implement. Training has more overhead and takes longer.
   - My understanding is that the current recommendation is that you train models when you want to alter their behavior, which doesn't seem to be needed here. We could potentially switch from GPT-4 to a lower cost model like GPT-3 (`gpt-3.5-turbo-instruct`) or even a model from a different provider and see a degradation
     in quality which might be bridged by training it with GPT-4's answers. If the cheaper model does worse, the first approach to try is to increase redundancies in the prompt and bring important elements towards the end of the prompt. Being shorter and concise helps, as does splitting up the problem into smaller steps.
   - Given the current example data, GPT-4 does just fine, and spending a premium on GPT-4 is going to be a better use of company money than paying an engineer to train a cheaper model unless there is very substantial usage.

  
