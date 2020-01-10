-- DROP VIEW public.test_summary_all_subjects_v;
CREATE OR REPLACE VIEW public.test_summary_all_subjects_v
AS WITH test_result_by_subject AS (
         SELECT test_summary_v.row_name[1] AS student_user_id,
            test_summary_v.row_name[2] AS cs_student_id,
            test_summary_v.row_name[3] AS assessment_id,
            test_summary_v.subject_1,
            test_summary_v.subject_2,
            test_summary_v.subject_3,
            test_summary_v.subject_4,
            test_summary_v.subject_5,
            COALESCE(NULLIF(test_summary_v.subject_1, 0::double precision), 0::double precision) + COALESCE(NULLIF(test_summary_v.subject_2, 0::double precision), 0::double precision) + COALESCE(NULLIF(test_summary_v.subject_3, 0::double precision), 0::double precision) + COALESCE(NULLIF(test_summary_v.subject_4, 0::double precision), 0::double precision) + COALESCE(NULLIF(test_summary_v.subject_5, 0::double precision), 0::double precision) AS total_mark
           FROM crosstab('select ARRAY[student_user_id::integer, cs_student_id::integer, assessment_id::integer] as row_name, testset_id, my_score
						   from (SELECT m.student_user_id,
						            s.student_id AS cs_student_id,
						            m.assessment_id,
						            m.testset_id,
						            m.score AS my_score,
						            m.total_score
						           FROM marking_summary_360_degree_mview m, student s
						          WHERE m.student_user_id = s.user_id) test_summary_v
						   order by 1,2'::text) test_summary_v(row_name integer[], subject_1 double precision, subject_2 double precision, subject_3 double precision, subject_4 double precision, subject_5 double precision, total_mark double precision)
        )
 SELECT trs.student_user_id,
    trs.cs_student_id::text AS cs_student_id,
    trs.assessment_id,
    a.test_center,
    trs.subject_1,
    trs.subject_2,
    trs.subject_3,
    trs.subject_4,
    trs.subject_5,
    trs.total_mark,
    rank() OVER (PARTITION BY trs.assessment_id ORDER BY trs.total_mark DESC) AS student_rank
   FROM test_result_by_subject trs,
    ( SELECT DISTINCT assessment_enroll.assessment_id,
            assessment_enroll.student_user_id,
            assessment_enroll.test_center
           FROM assessment_enroll) a
  WHERE trs.assessment_id = a.assessment_id AND trs.student_user_id = a.student_user_id;

-- Permissions

ALTER TABLE public.test_summary_all_subjects_v OWNER TO tailored;
GRANT ALL ON TABLE public.test_summary_all_subjects_v TO tailored;
