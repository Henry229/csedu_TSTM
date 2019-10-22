CREATE OR REPLACE VIEW public.my_report_progress_summary_v
AS SELECT e.student_id,
    p.id AS plan_id,
    d."order" AS assessment_order,
    p.name AS plan_name,
    d.assessment_id,
    p.year,
    p.grade,
    p.test_type
   FROM education_plan p,
    education_plan_details d,
    ( SELECT DISTINCT a.student_id,
            a.assessment_id
           FROM assessment_enroll a) e
  WHERE p.id = d.plan_id AND d.assessment_id = e.assessment_id
  ORDER BY d.plan_id, d."order";

-- Permissions

ALTER TABLE public.my_report_progress_summary_v OWNER TO tailored;
GRANT ALL ON TABLE public.my_report_progress_summary_v TO tailored;
