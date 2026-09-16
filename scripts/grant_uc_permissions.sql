-- Unity Catalog grants for the Integration Pattern Accelerator app.
--
-- Run ONCE, as a catalog admin, AFTER `databricks bundle deploy` has created
-- the app (the app's service principal only exists once the app is created).
--
-- Find the app's service principal client id with:
--   databricks apps get integ-pattern-react --profile fevm -o json \
--     | python3 -c "import sys,json;print(json.load(sys.stdin)['service_principal_client_id'])"
--
-- Then replace :sp below with that client id (a UUID), or run these statements
-- from a SQL editor with the value substituted.

-- The app SP needs to browse the catalog/schema and read/write/create volumes
-- for the generated integration packages.
GRANT USE CATALOG   ON CATALOG humana_payer                       TO `:sp`;
GRANT USE SCHEMA    ON SCHEMA  humana_payer.integration_pattern   TO `:sp`;
GRANT READ VOLUME   ON SCHEMA  humana_payer.integration_pattern   TO `:sp`;
GRANT WRITE VOLUME  ON SCHEMA  humana_payer.integration_pattern   TO `:sp`;
GRANT CREATE VOLUME ON SCHEMA  humana_payer.integration_pattern   TO `:sp`;
