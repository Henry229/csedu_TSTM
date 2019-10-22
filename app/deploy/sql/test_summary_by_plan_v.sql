CREATE OR REPLACE VIEW public.test_summary_by_plan_v
AS SELECT subject_t.plan_id,
    subject_t.student_id,
    subject_t.sum_my_score,
    subject_t.sum_avg_score,
    subject_t.sum_min_score,
    subject_t.sum_max_score,
    subject_t.rank_v
   FROM ( SELECT p.plan_id,
            ts.student_id,
            sum(ts.percentile_score) AS sum_my_score,
            sum(ts.avg_score) AS sum_avg_score,
            sum(ts.min_score) AS sum_min_score,
            sum(ts.max_score) AS sum_max_score,
            rank() OVER (PARTITION BY p.plan_id ORDER BY (sum(ts.percentile_score)) DESC) AS rank_v
           FROM csedu_education_plan_v p
             LEFT JOIN test_summary_mview ts ON p.assessment_id = ts.assessment_id AND p.testset_id = ts.testset_id
          WHERE ts.student_id IS NOT NULL
          GROUP BY p.plan_id, ts.student_id) subject_t;

-- Permissions

ALTER TABLE public.test_summary_by_plan_v OWNER TO dbuser;
GRANT ALL ON TABLE public.test_summary_by_plan_v TO dbuser;
