CREATE OR REPLACE VIEW public.csedu_plan_assessment_testsets_enrolled_v
AS SELECT cepv.plan_id,
    cepv.plan_name,
    cepv.year,
    cepv.grade,
    cepv.test_type,
    cepv."order",
    cepv.assessment_id,
    cepv.testset_id,
    cepv.subject,
    ae.id,
    ae.student_user_id,
    ae.attempt_count,
    ae.test_center,
    ae.start_time_client
   FROM csedu_education_plan_v cepv
     LEFT JOIN assessment_enroll ae ON ae.assessment_id = cepv.assessment_id AND ae.testset_id = cepv.testset_id
  ORDER BY cepv.plan_id, cepv."order", cepv.testset_id, ae.test_center, ae.student_user_id;

-- Permissions

ALTER TABLE public.csedu_plan_assessment_testsets_enrolled_v OWNER TO tailored;
GRANT ALL ON TABLE public.csedu_plan_assessment_testsets_enrolled_v TO tailored;
