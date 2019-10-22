CREATE OR REPLACE VIEW public.test_summary_by_center_v
AS SELECT d.plan_id,
    d."order" AS sequence,
    d.assessment_id,
    p.year,
    p.grade,
    p.test_type,
    a.name AS assessment_name,
    a.branch_id AS test_center
   FROM education_plan p,
    education_plan_details d,
    assessment a
  WHERE p.id = d.plan_id AND d.assessment_id = a.id AND (EXISTS ( SELECT 1
           FROM assessment_enroll e
          WHERE d.assessment_id = e.assessment_id))
  ORDER BY d."order";

-- Permissions

ALTER TABLE public.test_summary_by_center_v OWNER TO tailored;
GRANT ALL ON TABLE public.test_summary_by_center_v TO tailored;
