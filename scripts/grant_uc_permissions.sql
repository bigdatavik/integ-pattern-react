-- Unity Catalog grants for the Integration Pattern Accelerator app.
--
-- Run ONCE, as a catalog admin, AFTER `databricks bundle deploy` has created
-- the app (the app's service principal only exists once the app is created).
--
-- Substitute:
--   <catalog>  -> the UC catalog the app writes into (the `catalog` bundle var)
--   <schema>   -> the UC schema under it (the `schema` bundle var)
--   <sp>       -> the app's service principal client id (a UUID). Find it with:
--                  databricks apps get integ-pattern-react -p <profile> -o json \
--                    | python3 -c "import sys,json;print(json.load(sys.stdin)['service_principal_client_id'])"
--
-- The app SP needs to browse the catalog/schema and read/write/create volumes
-- for the generated integration packages.
GRANT USE CATALOG   ON CATALOG `<catalog>`                 TO `<sp>`;
GRANT USE SCHEMA    ON SCHEMA  `<catalog>`.`<schema>`      TO `<sp>`;
GRANT READ VOLUME   ON SCHEMA  `<catalog>`.`<schema>`      TO `<sp>`;
GRANT WRITE VOLUME  ON SCHEMA  `<catalog>`.`<schema>`      TO `<sp>`;
GRANT CREATE VOLUME ON SCHEMA  `<catalog>`.`<schema>`      TO `<sp>`;
