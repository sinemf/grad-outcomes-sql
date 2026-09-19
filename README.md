# What Is a Degree Worth in Canada?

SQL analysis of graduate employment outcomes, built from Statistics Canada's
public table 37-10-0280: median employment income of postsecondary graduates
two and five years after graduation, for the 2010-2019 graduating cohorts,
in constant 2024 dollars.

The raw release is a 1.7GB flat CSV with 5.5 million rows. This project ETLs
it into a normalized SQLite star schema (one fact table, eight dimension
tables, 4.2M facts after dropping suppressed cells) and answers eight
questions in pure SQL using joins, views, CTEs, and window functions.

## Pipeline

1. `build_db.py`: two-pass chunked ETL. Pass 1 scans the CSV for dimension
   values and builds lookup tables (splitting CIP codes out of field-of-study
   labels); pass 2 streams 5.5M rows into an integer-keyed fact table,
   dropping suppressed values, then indexes. Runs in ~1 minute.
2. `analysis.sql`: a reusable joined view over the star schema plus eight
   named analytical queries.
3. `run_analysis.py`: executes every named query, prints results, and saves
   each to `results/*.csv` (which also feed a dashboard).

## Selected findings (2017 cohort unless noted)

- **Credential payoff**: professional degrees lead ($117k median five years
  out); every credential level gains 12-29% between year two and year five.
- **Field matters more than province**: top undergraduate fields (computer
  science $99k, engineering $93k) out-earn the bottom by 2x+, while the
  provincial spread for the same degree is only about ±7% around the
  national median.
- **Growth vs starting salary**: sciences and math fields start mid-pack but
  grow earnings 29-37% from year two to five, the fastest of any group.
- **Gender gap**: five years out, women with undergraduate degrees earn less
  than men in nearly every field; the gap is widest in interdisciplinary
  computing (65 cents on the dollar).
- **International students** earn 67-99% of their Canadian classmates'
  medians depending on credential; the gap is smallest for professional and
  skilled-trades credentials.
- **Trend**: real (inflation-adjusted) early-career incomes fell from 2010
  to 2015 and have recovered since; the 2019 cohort earns 5.5% more than the
  2010 cohort did at the same point.
- **Caveat surfaced by Q8**: 8-20% of graduates have no income record
  (moved abroad, didn't file taxes), and coverage improved sharply after
  2014, so cross-cohort comparisons need care.

## Schema

```
fact_outcomes (cohort_year, geo_id, qualification_id, field_id, gender_id,
               age_group_id, student_status_id, characteristic_id,
               statistic_id, value)
  -> geography, qualification, field_of_study (with CIP code), gender,
     age_group, student_status, grad_characteristic, statistic
```

## Run it

```
python3 build_db.py      # expects data/37100280.csv from StatCan
python3 run_analysis.py
```

Or explore interactively: `sqlite3 grad_outcomes.db` then query `v_outcomes`.

## Source

Statistics Canada, Table 37-10-0280-01, "Characteristics and median
employment income of longitudinal cohorts of postsecondary graduates two and
five years after graduation, by educational qualification and field of study
(primary groupings)." Downloaded via the StatCan Web Data Service. Licensed
under the Statistics Canada Open Licence.
