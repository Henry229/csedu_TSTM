CREATE OR REPLACE VIEW public.csedu_education_plan_v
AS SELECT p.id AS plan_id,
    p.name AS plan_name,
    p.year,
    p.grade,
    p.test_type,
    d."order",
    d.assessment_id,
    a.testset_id,
    t.subject
   FROM education_plan p,
    education_plan_details d,
    assessment_testsets a,
    testset t
  WHERE p.id = d.plan_id AND d.assessment_id = a.assessment_id AND a.testset_id = t.id
  ORDER BY p.id, d."order", t.id;

-- Permissions

ALTER TABLE public.csedu_education_plan_v OWNER TO dbuser;
GRANT ALL ON TABLE public.csedu_education_plan_v TO dbuser;
