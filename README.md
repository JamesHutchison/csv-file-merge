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
