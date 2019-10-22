CREATE OR REPLACE VIEW public.test_summary_by_category_v
AS WITH org_score AS (
         SELECT m.assessment_id,
            m.testset_id,
            m.code_name,
            m.student_id,
            m.score,
            m.total_score,
            m.score * 100::double precision / m.total_score AS percentile_score
           FROM marking_summary_by_category_360_degree_mview m
          WHERE m."grouping" = 'by_student'::text
        ), calculated_score AS (
         SELECT org_score.assessment_id,
            org_score.testset_id,
            org_score.code_name,
            org_score.student_id,
            org_score.percentile_score,
            count(org_score.student_id) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name) AS total_students,
            avg(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name) AS avg_score,
            max(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name) AS max_score,
            min(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name) AS min_score,
            stddev(org_score.percentile_score) OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name) AS stddev_v,
            rank() OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name ORDER BY org_score.percentile_score DESC) AS rank_v,
            percent_rank() OVER (PARTITION BY org_score.assessment_id, org_score.testset_id, org_score.code_name ORDER BY org_score.percentile_score DESC) * 100::double precision AS percent_rank_v
           FROM org_score
        ), statical_score AS (
         SELECT org_score.assessment_id,
            org_score.testset_id,
            org_score.code_name,
            percentile_cont(0.50::double precision) WITHIN GROUP (ORDER BY org_score.percentile_score) AS median,
            percentile_cont(0.20::double precision) WITHIN GROUP (ORDER BY org_score.percentile_score) AS percentile_20,
            percentile_cont(0.80::double precision) WITHIN GROUP (ORDER BY org_score.percentile_score) AS percentile_80
           FROM org_score
          GROUP BY org_score.assessment_id, org_score.testset_id, org_score.code_name
        )
 SELECT t1.assessment_id,
    t1.testset_id,
    t1.code_name,
    t1.student_id,
    t1.score,
    t1.total_score,
    t1.percentile_score,
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
  WHERE t1.assessment_id = t2.assessment_id AND t1.testset_id = t2.testset_id AND t1.code_name::text = t2.code_name::text AND t1.assessment_id = t3.assessment_id AND t1.testset_id = t3.testset_id AND t1.student_id = t3.student_id AND t1.code_name::text = t3.code_name::text;

-- Permissions

ALTER TABLE public.test_summary_by_category_v OWNER TO tailored;
GRANT ALL ON TABLE public.test_summary_by_category_v TO tailored;
