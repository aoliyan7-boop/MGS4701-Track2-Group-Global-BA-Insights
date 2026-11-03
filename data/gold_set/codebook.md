# Gold Set Coding Rules (Codebook)

This document defines the rules used by Coder B to manually code the 30-item blind set (`my_blind_coding.xlsx`). It is used to validate the automated extraction done by Coder A.

**Coding Guidelines:**
- **Excel**: `1` if the job description explicitly mentions Excel (or spreadsheet software). `0` otherwise.
- **SQL**: `1` if the job description explicitly mentions SQL (or querying databases). `0` otherwise.
- **ai_skill_explicit**: `1` if the job description explicitly mentions AI tools (e.g., ChatGPT, Copilot, Machine Learning, GenAI, LLM). `0` otherwise.

**Note:** We only look at explicit mentions. If it says "experience with data tools", we do not assume SQL. It must be explicitly named.
