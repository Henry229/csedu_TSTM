CREATE MATERIALIZED VIEW public.marking_summary_360_degree_mview
TABLESPACE pg_default
AS WITH marking_summary AS (
         SELECT e.assessment_id,
            m.testset_id,
            e.student_id,
            GROUPING(e.assessment_id, m.testset_id, e.student_id) AS "grouping",
            count(DISTINCT e.student_id) AS number_of_candidates,
            sum(m.candidate_mark * m.weight) AS score,
            sum(m.outcome_score * m.weight) AS total_score
           FROM marking m,
            assessment_enroll e
          WHERE m.assessment_enroll_id = e.id
          GROUP BY ROLLUP(e.assessment_id, m.testset_id, e.student_id)
          ORDER BY e.assessment_id, m.testset_id, e.student_id
        )
 SELECT marking_summary.assessment_id,
    marking_summary.testset_id,
    marking_summary.student_id,
        CASE
            WHEN marking_summary."grouping" = 0 THEN 'by_student'::text
            WHEN marking_summary."grouping" = 1 THEN 'by_subject'::text
            WHEN marking_summary."grouping" = 3 THEN 'by_assessment'::text
            ELSE 'other'::text
        END AS "grouping",
    marking_summary.number_of_candidates,
    marking_summary.score,
    marking_summary.total_score
   FROM marking_summary
  WHERE marking_summary.assessment_id IS NOT NULL
WITH DATA;

-- Permissions

ALTER TABLE public.marking_summary_360_degree_mview OWNER TO dbuser;
GRANT ALL ON TABLE public.marking_summary_360_degree_mview TO dbuser;
