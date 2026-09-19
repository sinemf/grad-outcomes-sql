-- ===========================================================================
-- What is a degree worth in Canada?
-- SQL analysis of StatCan 37-10-0280: median employment income of
-- postsecondary graduates, 2 and 5 years after graduation (2024 dollars).
--
-- Default slice unless a query says otherwise: both genders, ages 15-64,
-- Canadian + international students, graduates reporting employment income.
-- ===========================================================================

-- A readable view over the star schema (join all 8 dimensions once).
DROP VIEW IF EXISTS v_outcomes;
CREATE VIEW v_outcomes AS
SELECT f.cohort_year,
       g.name   AS geo,
       q.name   AS qualification,
       fs.name  AS field,
       fs.cip_code,
       gen.name AS gender,
       ag.name  AS age_group,
       ss.name  AS student_status,
       ch.name  AS characteristic,
       st.name  AS statistic,
       f.value
FROM fact_outcomes f
JOIN geography           g   ON g.id   = f.geo_id
JOIN qualification       q   ON q.id   = f.qualification_id
JOIN field_of_study      fs  ON fs.id  = f.field_id
JOIN gender              gen ON gen.id = f.gender_id
JOIN age_group           ag  ON ag.id  = f.age_group_id
JOIN student_status      ss  ON ss.id  = f.student_status_id
JOIN grad_characteristic ch  ON ch.id  = f.characteristic_id
JOIN statistic           st  ON st.id  = f.statistic_id;

-- ---------------------------------------------------------------------------
-- Q1. What is each credential worth? Median income 2 vs 5 years out,
--     and how much incomes grow in between. (pivot with CASE + CTE)
-- ---------------------------------------------------------------------------
-- name: q1_credential_payoff
WITH slice AS (
    SELECT qualification, statistic, value
    FROM v_outcomes
    WHERE cohort_year = 2017 AND geo = 'Canada'
      AND field = 'Total, field of study'
      AND gender = 'Total, gender' AND age_group = '15 to 64 years'
      AND student_status = 'Canadian and international students'
      AND characteristic = 'Graduates reporting employment income'
      AND qualification <> 'Total, educational qualification'
)
SELECT qualification,
       MAX(CASE WHEN statistic LIKE 'Median%two years%'  THEN value END) AS income_2yr,
       MAX(CASE WHEN statistic LIKE 'Median%five years%' THEN value END) AS income_5yr,
       ROUND(100.0 * (MAX(CASE WHEN statistic LIKE 'Median%five years%' THEN value END)
             / MAX(CASE WHEN statistic LIKE 'Median%two years%' THEN value END) - 1), 1)
             AS growth_pct
FROM slice
GROUP BY qualification
HAVING income_2yr IS NOT NULL
ORDER BY income_5yr DESC;

-- ---------------------------------------------------------------------------
-- Q2. Which undergraduate fields pay best 5 years out, and how big are they?
--     (join of two statistics + RANK window function)
-- ---------------------------------------------------------------------------
-- name: q2_top_fields
WITH base AS (
    SELECT field, statistic, value
    FROM v_outcomes
    WHERE cohort_year = 2017 AND geo = 'Canada'
      AND qualification = 'Undergraduate degree'
      AND gender = 'Total, gender' AND age_group = '15 to 64 years'
      AND student_status = 'Canadian and international students'
      AND characteristic = 'Graduates reporting employment income'
      AND field <> 'Total, field of study'
),
pivoted AS (
    SELECT field,
           MAX(CASE WHEN statistic LIKE 'Median%five years%' THEN value END) AS income_5yr,
           MAX(CASE WHEN statistic = 'Number of graduates'   THEN value END) AS graduates
    FROM base GROUP BY field
)
SELECT RANK() OVER (ORDER BY income_5yr DESC) AS rnk,
       field, CAST(income_5yr AS INT) AS income_5yr, CAST(graduates AS INT) AS graduates
FROM pivoted
WHERE income_5yr IS NOT NULL
ORDER BY rnk
LIMIT 15;

-- ---------------------------------------------------------------------------
-- Q3. Where do earnings grow fastest between year 2 and year 5?
--     High growth can matter more than a high starting salary.
-- ---------------------------------------------------------------------------
-- name: q3_fastest_growth
WITH base AS (
    SELECT field, statistic, value
    FROM v_outcomes
    WHERE cohort_year = 2017 AND geo = 'Canada'
      AND qualification = 'Undergraduate degree'
      AND gender = 'Total, gender' AND age_group = '15 to 64 years'
      AND student_status = 'Canadian and international students'
      AND characteristic = 'Graduates reporting employment income'
      AND field <> 'Total, field of study'
)
SELECT field,
       CAST(MAX(CASE WHEN statistic LIKE 'Median%two years%'  THEN value END) AS INT) AS income_2yr,
       CAST(MAX(CASE WHEN statistic LIKE 'Median%five years%' THEN value END) AS INT) AS income_5yr,
       ROUND(100.0 * (MAX(CASE WHEN statistic LIKE 'Median%five years%' THEN value END)
             / MAX(CASE WHEN statistic LIKE 'Median%two years%' THEN value END) - 1), 1) AS growth_pct
FROM base
GROUP BY field
HAVING income_2yr IS NOT NULL AND income_5yr IS NOT NULL
ORDER BY growth_pct DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- Q4. Same degree, different province: undergrad incomes vs the national
--     median. (window function over a filtered slice)
-- ---------------------------------------------------------------------------
-- name: q4_provinces
WITH prov AS (
    SELECT geo, value AS income_5yr
    FROM v_outcomes
    WHERE cohort_year = 2017
      AND qualification = 'Undergraduate degree'
      AND field = 'Total, field of study'
      AND gender = 'Total, gender' AND age_group = '15 to 64 years'
      AND student_status = 'Canadian and international students'
      AND characteristic = 'Graduates reporting employment income'
      AND statistic LIKE 'Median%five years%'
)
SELECT geo, CAST(income_5yr AS INT) AS income_5yr,
       ROUND(100.0 * income_5yr /
             MAX(CASE WHEN geo = 'Canada' THEN income_5yr END) OVER () - 100, 1)
             AS vs_canada_pct
FROM prov
ORDER BY income_5yr DESC;

-- ---------------------------------------------------------------------------
-- Q5. Gender earnings gap 5 years after an undergraduate degree, by field.
--     (self-pivot on the gender dimension)
-- ---------------------------------------------------------------------------
-- name: q5_gender_gap
WITH base AS (
    SELECT field, gender, value
    FROM v_outcomes
    WHERE cohort_year = 2017 AND geo = 'Canada'
      AND qualification = 'Undergraduate degree'
      AND age_group = '15 to 64 years'
      AND student_status = 'Canadian and international students'
      AND characteristic = 'Graduates reporting employment income'
      AND statistic LIKE 'Median%five years%'
      AND gender IN ('Man', 'Woman')
      AND field <> 'Total, field of study'
)
SELECT field,
       CAST(MAX(CASE WHEN gender = 'Woman' THEN value END) AS INT) AS women,
       CAST(MAX(CASE WHEN gender = 'Man'   THEN value END) AS INT) AS men,
       ROUND(100.0 * MAX(CASE WHEN gender = 'Woman' THEN value END)
             / MAX(CASE WHEN gender = 'Man' THEN value END), 1) AS women_pct_of_men
FROM base
GROUP BY field
HAVING women IS NOT NULL AND men IS NOT NULL
ORDER BY women_pct_of_men ASC
LIMIT 12;

-- ---------------------------------------------------------------------------
-- Q6. International vs Canadian students: median income 2 years out,
--     by credential.
-- ---------------------------------------------------------------------------
-- name: q6_international
SELECT qualification,
       CAST(MAX(CASE WHEN student_status = 'Canadian students'      THEN value END) AS INT) AS canadian,
       CAST(MAX(CASE WHEN student_status = 'International students' THEN value END) AS INT) AS international,
       ROUND(100.0 * MAX(CASE WHEN student_status = 'International students' THEN value END)
             / MAX(CASE WHEN student_status = 'Canadian students' THEN value END), 1)
             AS intl_pct_of_cdn
FROM v_outcomes
WHERE cohort_year = 2017 AND geo = 'Canada'
  AND field = 'Total, field of study'
  AND gender = 'Total, gender' AND age_group = '15 to 64 years'
  AND characteristic = 'Graduates reporting employment income'
  AND statistic LIKE 'Median%two years%'
  AND qualification <> 'Total, educational qualification'
GROUP BY qualification
HAVING canadian IS NOT NULL AND international IS NOT NULL
ORDER BY canadian DESC;

-- ---------------------------------------------------------------------------
-- Q7. Are new graduates earning more than they used to? Cohort-over-cohort
--     trend in constant dollars. (LAG window function)
-- ---------------------------------------------------------------------------
-- name: q7_cohort_trend
WITH trend AS (
    SELECT cohort_year, value AS income_2yr
    FROM v_outcomes
    WHERE geo = 'Canada'
      AND qualification = 'Undergraduate degree'
      AND field = 'Total, field of study'
      AND gender = 'Total, gender' AND age_group = '15 to 64 years'
      AND student_status = 'Canadian and international students'
      AND characteristic = 'Graduates reporting employment income'
      AND statistic LIKE 'Median%two years%'
)
SELECT cohort_year, CAST(income_2yr AS INT) AS income_2yr,
       CAST(income_2yr - LAG(income_2yr) OVER (ORDER BY cohort_year) AS INT)
           AS change_vs_prev_cohort,
       ROUND(100.0 * income_2yr / FIRST_VALUE(income_2yr)
             OVER (ORDER BY cohort_year) - 100, 1) AS vs_2010_pct
FROM trend
ORDER BY cohort_year;

-- ---------------------------------------------------------------------------
-- Q8. Data-quality check: what share of each cohort has no income record
--     (left the country, no tax filing)? Medians only describe the rest.
-- ---------------------------------------------------------------------------
-- name: q8_coverage
SELECT cohort_year,
       CAST(MAX(CASE WHEN characteristic = 'All graduates' THEN value END) AS INT)
           AS all_graduates,
       CAST(MAX(CASE WHEN characteristic = 'Graduates with no income information'
                THEN value END) AS INT) AS no_income_info,
       ROUND(100.0 * MAX(CASE WHEN characteristic = 'Graduates with no income information'
             THEN value END)
             / MAX(CASE WHEN characteristic = 'All graduates' THEN value END), 1)
           AS missing_pct
FROM v_outcomes
WHERE geo = 'Canada'
  AND qualification = 'Total, educational qualification'
  AND field = 'Total, field of study'
  AND gender = 'Total, gender' AND age_group = '15 to 64 years'
  AND student_status = 'Canadian and international students'
  AND statistic = 'Number of graduates'
GROUP BY cohort_year
ORDER BY cohort_year;
