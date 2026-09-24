# Data Dictionary - Track 2: International BA Labor Market

This document defines the fields, data types, and processing rules for all datasets in this project.
**Version**: v1.0 (Pilot Stage)
**Last Updated**: 2026-09-XX
**Owner**: Member B (Data Cleaning & Repository Lead)

## 1. Raw Data Fields

| Column Name | Type | Description | Example | Missing Value Rule |
| :--- | :--- | :--- | :--- | :--- |
| `job_id` | String | Unique identifier (e.g., hash of URL or auto-increment) | `a1b2c3d4` | Not allowed. If missing, regenerate. |
| `job_title` | String | Job title | `Business Analyst` | Not allowed. Drop record if missing. |
| `company` | String | Company name | `Google` | Fill with `Unknown` |
| `industry` | String | Industry classification | `Technology` | Fill with `Unknown` |
| `city` | String | City of the job | `London` | Fill with `Unknown` |
| `country` | String | Country | `UK` | Infer from city, or fill `Unknown` |
| `salary_min` | Float | Minimum annual salary | `50000.0` | Keep as NaN if missing |
| `salary_max` | Float | Maximum annual salary | `80000.0` | Keep as NaN if missing |
| `salary_currency` | String | Salary currency | `GBP` | Fill with `Unknown` |
| `salary_is_predicted` | Boolean | Whether salary is model-predicted (Adzuna API) | `True` / `False` | Default to `False` |
| `experience` | String | Experience requirement | `2+ years` | Fill with `Not Specified` |
| `education` | String | Education requirement | `Bachelor's` | Fill with `Not Specified` |
| `jd_text` | Text | Full job description | `We are looking for...` | Not allowed. Drop record if missing. |
| `date_posted` | Date | Date posted (YYYY-MM-DD) | `2026-09-01` | Fill with collection date |
| `url` | String | Original job posting URL | `https://...` | Not allowed. Drop record if missing. |
| `source` | String | Data source platform | `LinkedIn` / `Adzuna` | Not allowed. |

## 2. Cleaning Rules

1. **Deduplication**: Deduplicate based on `url` or `job_title` + `company`.
2. **Missing Values**: Follow the "Missing Value Rule" column strictly.
3. **Encoding**: 
   - Convert `salary_is_predicted` to 0/1 boolean.
   - Convert `date_posted` to standard datetime format.
4. **Text Cleaning**: Remove HTML tags, extra spaces, and newlines from `jd_text`.

## 3. Known Biases
- Platform bias: LinkedIn and Adzuna samples may have industry or regional biases.
- Salary bias: Adzuna's predicted salaries (`salary_is_predicted=True`) may differ from actual salaries and should be flagged separately in analysis.
