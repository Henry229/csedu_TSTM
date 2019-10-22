CREATE OR REPLACE VIEW public.item_score_summary_v
AS WITH marking_summary AS (
         SELECT m.item_id,
            ae.assessment_id,
            GROUPING(m.item_id, ae.assessment_id) AS "grouping",
            a2.name AS assessment_name,
            count(m.is_correct) AS number_of_exec,
            sum(
                CASE m.is_correct
                    WHEN true THEN 1
                    ELSE 0
                END) AS number_of_correct
           FROM marking m,
            assessment_enroll ae,
            assessment a2
          WHERE m.assessment_enroll_id = ae.id AND ae.assessment_id = a2.id
          GROUP BY ROLLUP(m.item_id, ae.assessment_id), a2.name
          ORDER BY m.item_id, ae.assessment_id
        )
 SELECT marking_summary.item_id,
    marking_summary.assessment_id,
        CASE
            WHEN marking_summary."grouping" = 0 THEN 'by_item_assessment'::text
            WHEN marking_summary."grouping" = 1 THEN 'by_item'::text
            ELSE 'other'::text
        END AS "grouping",
    marking_summary.assessment_name,
    marking_summary.number_of_exec,
    marking_summary.number_of_correct,
    marking_summary.number_of_correct::double precision / marking_summary.number_of_exec::double precision * 100::double precision AS percentile_correct
   FROM marking_summary
  WHERE marking_summary.item_id IS NOT NULL;

-- Permissions

ALTER TABLE public.item_score_summary_v OWNER TO dbuser;
GRANT ALL ON TABLE public.item_score_summary_v TO dbuser;
