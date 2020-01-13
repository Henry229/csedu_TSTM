CREATE OR REPLACE VIEW public.test_summary_by_assessment_v
AS WITH org_v AS (
         SELECT p.plan_id,
            p."order",
            p.assessment_id,
            ts.student_user_id,
            sum(ts.percentile_score) AS score,
            rank() OVER (PARTITION BY p.plan_id, p."order", p.assessment_id ORDER BY (sum(ts.percentile_score)) DESC) AS rank_v
           FROM csedu_education_plan_v p
             LEFT JOIN test_summary_mview ts ON p.assessment_id = ts.assessment_id AND p.testset_id = ts.testset_id
          GROUP BY p.plan_id, p."order", p.assessment_id, ts.student_user_id
          ORDER BY p."order"
        )
 SELECT o.plan_id,
    o."order",
    o.assessment_id,
    o.student_user_id,
    o.score,
    o.rank_v,
    avg(o.score) OVER (PARTITION BY o.plan_id, o.assessment_id) AS avg_score
   FROM org_v o;

-- Permissions

ALTER TABLE public.test_summary_by_assessment_v OWNER TO tailored;
GRANT ALL ON TABLE public.test_summary_by_assessment_v TO tailored;
