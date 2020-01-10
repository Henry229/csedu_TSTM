SELECT 'DROP VIEW IF EXISTS ' || table_name || ' CASCADE;'
  FROM information_schema.views
 WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
   AND table_name !~ '^pg_'
UNION
SELECT 'DROP MATERIALIZED VIEW IF EXISTS ' || oid::regclass::text || ' CASCADE;'
FROM   pg_class
WHERE  relkind = 'm'
