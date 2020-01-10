CREATE OR REPLACE VIEW public.my_report_list_v
AS WITH marked_ts_list AS (
         SELECT crosstab.assessment_id,
            crosstab.subject_1,
            crosstab.subject_2,
            crosstab.subject_3,
            crosstab.subject_4,
            crosstab.subject_5
           FROM crosstab('select distinct marking.assessment_id, marking.assessment_id, marking.testset_id 
							from (SELECT DISTINCT assessment_enroll.assessment_id, marking.testset_id
							   		FROM marking,
							   			 assessment_enroll
							  		WHERE marking.assessment_enroll_id = assessment_enroll.id) marking
							order by 1,2,3'::text) crosstab(assessment_id integer, subject_1 integer, subject_2 integer, subject_3 integer, subject_4 integer, subject_5 integer)
        )
 SELECT DISTINCT a.id,
    m.assessment_id,
    e.student_user_id,
    to_char(a.session_date, 'YYYY'::text) AS year,
    a.test_type,
    a.name,
    a.branch_id,
    a.session_date,
    m.subject_1,
    m.subject_2,
    m.subject_3,
    m.subject_4,
    m.subject_5
   FROM marked_ts_list m
     RIGHT JOIN assessment_enroll e ON m.assessment_id = e.assessment_id
     JOIN assessment a ON e.assessment_id = a.id;

-- Permissions

ALTER TABLE public.my_report_list_v OWNER TO tailored;
GRANT ALL ON TABLE public.my_report_list_v TO tailored;
