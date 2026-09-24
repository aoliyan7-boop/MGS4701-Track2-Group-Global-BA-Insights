# Data Dictionary - Track 2: International BA Labor Market

**Version**: v1.1 (Pilot Stage - Updated with real data)
**Last Updated**: 2026-09-24
**Owner**: Member B (Data Cleaning & Repository Lead)

## 1. Raw Data Fields (100 Records)

| Column Name | Type | Description | Example | Missing Value Rule |
| :--- | :--- | :--- | :--- | :--- |
| `Job_id` | String | Unique identifier | `BA0001` | Not allowed |
| `Country` | String | Country of the job | `United States` | Fill with `Unknown` |
| `City` | String | City of the job | `Atlanta, GA` | Fill with `Unknown` |
| `Job_Title` | String | Job title | `Staff Business Analyst` | Not allowed |
| `Company_Name` | String | Company name | `TriNet` | Fill with `Unknown` |
| `Industry` | String | Industry classification | `Technology` | Fill with `Unknown` |
| `Source` | String | Data source platform | `LinkedIn` | Not allowed |
| `Job_Url` | String | Original job posting URL | `https://...` | Not allowed |
| `Date_Posted` | Date | Date posted (YYYY-MM-DD) | `2026-07-16` | Fill with collection date |
| `Date_Collected` | Date | Date collected (YYYY-MM-DD) | `2026-09-15` | Not allowed |
| `Salary_Min` | Float | Minimum annual salary | `89600` | Keep as NaN if missing |
| `Salary_Max` | Float | Maximum annual salary | `179200` | Keep as NaN if missing |
| `Salary_Currency` | String | Salary currency | `USD` / `GBP` | Fill with `Unknown` |
| `Experience_Min` | Float | Minimum years of experience | `8` | Fill with `Not Specified` |
| `Experience_Max` | Float | Maximum years of experience | `10` | Fill with `Not Specified` |
| `Education` | String | Education requirement | `Bachelor's` | Fill with `Not Specified` |
| `Excel` | Boolean | Requires Excel (0/1) | `1` | Fill with `0` |
| `SQL` | Boolean | Requires SQL (0/1) | `1` | Fill with `0` |
| `Python` | Boolean | Requires Python (0/1) | `0` | Fill with `0` |
| `R` | Boolean | Requires R (0/1) | `0` | Fill with `0` |
| `Tableau` | Boolean | Requires Tableau (0/1) | `1` | Fill with `0` |
| `Power_BI` | Boolean | Requires Power BI (0/1) | `0` | Fill with `0` |
| `AI_tools` | Boolean | Mentions AI tools (0/1) | `1` | Fill with `0` |
| `JD_text` | Text | Full job description | `TriNet is a leading...` | Not allowed |
| `Collector` | String | Initials of data collector | `A` | Not allowed |

## 2. Cleaning Rules Applied
1. **Deduplication**: Removed duplicates based on `Job_Url` (0 duplicates found in pilot).
2. **Missing Values**: 
   - `Education`, `Industry`, `Experience_Min`, `Experience_Max` filled with `'Not Specified'` or `'Unknown'`.
   - `Salary_Min` and `Salary_Max` kept as `NaN` (not zero) to avoid skewing averages.
3. **Skill Encoding**: Ensured all skill columns (`Excel`, `SQL`, etc.) are strictly 0 or 1.
4. **Date Formatting**: Converted `Date_Posted` and `Date_Collected` to datetime objects.

## 3. Known Biases
- **Platform Bias**: Only LinkedIn data from the US, UK, Singapore, and Hong Kong.
- **Salary Bias**: 66% of records have missing salary data (only 33/100 have `Salary_Min`). This may bias salary analysis.
- **AI Tools Bias**: Only 12% of postings explicitly mention AI tools; this may underrepresent actual AI usage.
