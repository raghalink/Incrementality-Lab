create warehouse if not exists abtest
 warehouse_size = 'XSMALL'
 auto_suspend = 60
 auto_resume = true
 initially_suspended = true
 
use role SYSADMIN;
create database if not exists AB_DB;
create schema if not exists AB_DB.RAW;
create schema if not exists AB_DB.ANALYTICS;
