USE DATABASE AB_DB;
USE SCHEMA RAW;

CREATE OR REPLACE TABLE criteo_uplift (
    user_id INTEGER,
    f0 FLOAT,
    f1 FLOAT,
    f2 FLOAT,
    f3 FLOAT,
    f4 FLOAT,
    f5 FLOAT,
    f6 FLOAT,
    f7 FLOAT,
    f8 FLOAT,
    f9 FLOAT,
    f10 FLOAT,
    f11 FLOAT,
    treatment INTEGER,
    conversion INTEGER,
    visit INTEGER,
    exposure INTEGER
);