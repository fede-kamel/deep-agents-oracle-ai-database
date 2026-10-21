-- OPERATOR STEP, as ADMIN, in your own terminal (SQLcl or SQL*Plus):
--   sql admin@<your TLS connect string> @sql/01_users.sql
-- Creates the schema owner and one agent user per patient. The passwords are
-- prompted without echo and are never written anywhere by this script. They
-- are used only inside PL/SQL, so an error prints the ORA code, not the
-- statement that holds the password.
SET VERIFY OFF
SET SERVEROUTPUT ON
ACCEPT owner_pw CHAR PROMPT 'Password for SAMPLE_OWNER (not echoed): ' HIDE
ACCEPT agent_pw CHAR PROMPT 'Password for SAMPLE_AGENT_A (not echoed): ' HIDE

DECLARE
  -- The tablespace for user data: DATA on Autonomous Database, USERS elsewhere.
  ts VARCHAR2(30);
BEGIN
  SELECT NVL(MAX(tablespace_name), 'USERS') INTO ts
    FROM dba_tablespaces WHERE tablespace_name = 'DATA';
  EXECUTE IMMEDIATE 'CREATE USER sample_owner IDENTIFIED BY "&owner_pw"'
    || ' DEFAULT TABLESPACE ' || ts || ' QUOTA 100M ON ' || ts;
  -- The agent for synthetic patient A. It may create tables in its own schema
  -- only, for the LangGraph checkpoints; everything else is granted by the owner.
  EXECUTE IMMEDIATE 'CREATE USER sample_agent_a IDENTIFIED BY "&agent_pw"'
    || ' DEFAULT TABLESPACE ' || ts || ' QUOTA 64M ON ' || ts;
  DBMS_OUTPUT.PUT_LINE('Created SAMPLE_OWNER and SAMPLE_AGENT_A in ' || ts || '.');
END;
/

GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER TO sample_owner;
GRANT EXECUTE ON DBMS_RLS TO sample_owner;
GRANT CREATE SESSION, CREATE TABLE TO sample_agent_a;

UNDEFINE owner_pw
UNDEFINE agent_pw
