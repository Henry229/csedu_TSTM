CREATE OR REPLACE VIEW public.test_summary_by_subject_v
AS SELECT subject_t.plan_id,
    subject_t.testset_id,
    subject_t.student_id,
    subject_t.subject_avg_my_score,
    subject_t.subject_avg_avg_score,
    subject_t.subject_avg_min_score,
    subject_t.subject_avg_max_score,
    subject_t.rank_v
   FROM ( SELECT p.plan_id,
            p.testset_id,
            ts.student_id,
            avg(ts.percentile_score) AS subject_avg_my_score,
            avg(ts.avg_score) AS subject_avg_avg_score,
            avg(ts.min_score) AS subject_avg_min_score,
            avg(ts.max_score) AS subject_avg_max_score,
            rank() OVER (PARTITION BY p.plan_id, p.testset_id ORDER BY (avg(ts.percentile_score)) DESC) AS rank_v
           FROM csedu_education_plan_v p
             LEFT JOIN test_summary_mview ts ON p.assessment_id = ts.assessment_id AND p.testset_id = ts.testset_id
          GROUP BY p.plan_id, p.testset_id, ts.student_id) subject_t;

-- Permissions

ALTER TABLE public.test_summary_by_subject_v OWNER TO tailored;
GRANT ALL ON TABLE public.test_summary_by_subject_v TO tailored;
