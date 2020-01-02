CREATE OR REPLACE VIEW public.my_report_body_v
AS SELECT m.assessment_enroll_id,
    m.testset_id,
    e.student_user_id,
    e.grade,
    m.created_time,
    m.candidate_r_value,
    m.is_correct,
    m.correct_r_value,
    get_marking_item_percentage(e.assessment_id, m.testset_id, m.item_id) AS item_percentile,
    m.item_id,
    i.category
   FROM marking m,
    assessment_enroll e,
    item i
  WHERE e.id = m.assessment_enroll_id AND i.id = m.item_id;

-- Permissions

ALTER TABLE public.my_report_body_v OWNER TO tailored;
GRANT ALL ON TABLE public.my_report_body_v TO tailored;
