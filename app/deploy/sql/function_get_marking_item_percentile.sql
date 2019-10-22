create or replace function get_marking_item_percentage 
(_assessment_id integer, _testset_id integer, _item_id integer)
RETURNS integer AS $_percentile$
declare
    _percentile integer;
BEGIN  
  SELECT 100*COALESCE(sum(CASE WHEN is_correct THEN 1 ELSE 0 END),0)/count(DISTINCT e.id) AS correct_percentile
  into _percentile
  FROM marking m,
    assessment_enroll e
  WHERE m.assessment_enroll_id = e.id
  and e.assessment_id = $1
  and m.testset_id = $2
  and m.item_id = $3;
 return _percentile;
END;  
$_percentile$ LANGUAGE plpgsql;