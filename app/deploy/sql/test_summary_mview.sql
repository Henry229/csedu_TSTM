CREATE MATERIALIZED VIEW public.test_summary_mview
TABLESPACE pg_default
AS WITH org_score AS (
         SELECT marking_summary_360_degree_mview.assessment_id,
            marking_summary_360_degree_mview.testset_id,
            marking_summary_360_degree_mview.student_user_id,
            marking_summary_360_degree_mview.score,
            marking_summary_360_degree_mview.total_score,
            marking_summary_360_degree_mview.score * 100::double precision / marking_summary_360_degree_mview.total_score AS percentile_score,
            (marking_summary_360_degree_mview.score - avg(marking_summary_360_degree_mview.score) OVER (PARTITION BY marking_summary_360_degree_mview.assessment_id, marking_summary_360_degree_mview.testset_id)) /
                CASE stddev(marking_summary_360_degree_mview.score) OVER (PARTITION BY marking_summary_360_degree_mview.assessment_id, marking_summary_360_degree_mview.testset_id)
                    WHEN 0 THEN 0.01::double precision
                    ELSE stddev(marking_summary_360_degree_mview.score) OVER (PARTITION BY marking_summary_360_degree_mview.assessment_id, marking_summary_360_degree_mview.testset_id)
                END AS z_score,
            (marking_summary_360_degree_mview.score - avg(marking_summary_360_degree_mview.score) OVER (PARTITION BY marking_summary_360_degree_mview.assessment_id, marking_summary_360_degree_mview.testset_id)) /
                CASE stddev(marking_summary_360_degree_mview.score) OVER (PARTITION BY marking_summary_360_degree_mview.assessment_id, marking_summary_360_degree_mview.testset_id)
                    WHEN 0 THEN 0.01::double precision
                    ELSE stddev(marking_summary_360_degree_mview.score) OVER (PARTITION BY marking_summary_360_degree_mview.assessment_id, marking_summary_360_degree_mview.testset_id)
                END * 10::double precision + 50::double precision AS standard_score
           FROM marking_summary_360_degree_mview
          WHERE marking_summary_360_degree_mview."grouping" = 'by_student'::text
        ), calculated_score AS (
         SELECT org_score.assessment_id,
            org_score.testset_id,
            org_score.student_user_id,
            org_score.percentile_score,
            count(org_score.student_user_id) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id) AS total_students,
            avg(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id) AS avg_score,
            max(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id) AS max_score,
            min(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id) AS min_score,
            stddev(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id) AS stddev_v,
            rank() OVER (PARTITION BY org_score.assessment_id, org_score.testset_id ORDER BY org_score.percentile_score DESC) AS rank_v,
            percent_rank() OVER (PARTITION BY org_score.assessment_id, org_score.testset_id ORDER BY org_score.percentile_score DESC) * 100::double precision AS percent_rank_v
           FROM org_score
        ), statical_score AS (
         SELECT org_score.assessment_id,
            org_score.testset_id,
            percentile_cont(0.50::double precision) WITHIN GROUP (ORDER BY org_score.percentile_score) AS median,
            percentile_cont(0.20::double precision) WITHIN GROUP (ORDER BY org_score.percentile_score) AS percentile_20,
            percentile_cont(0.80::double precision) WITHIN GROUP (ORDER BY org_score.percentile_score) AS percentile_80
           FROM org_score
          GROUP BY org_score.assessment_id, org_score.testset_id
        )
 SELECT t1.assessment_id,
    t1.testset_id,
    t1.student_user_id,
    t1.score,
    t1.total_score,
    t1.percentile_score,
    t1.z_score,
    t1.standard_score,
    t3.total_students,
    t3.avg_score,
    t3.max_score,
    t3.min_score,
    t3.stddev_v,
    t3.rank_v,
    t3.percent_rank_v,
    t2.median,
    t2.percentile_20,
    t2.percentile_80
   FROM org_score t1,
    statical_score t2,
    calculated_score t3
  WHERE t1.assessment_id = t2.assessment_id AND t1.testset_id = t2.testset_id AND t1.assessment_id = t3.assessment_id AND t1.testset_id = t3.testset_id AND t1.student_user_id = t3.student_user_id
WITH DATA;

-- Permissions

ALTER TABLE public.test_summary_mview OWNER TO tailored;
GRANT ALL ON TABLE public.test_summary_mview TO tailored;
