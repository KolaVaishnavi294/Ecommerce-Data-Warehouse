-- sql/02_warehouse_ddl.sql
-- =============================================================================
-- DATA WAREHOUSE SCHEMA — Star Schema (OLAP)
-- Dimensional model for analytical querying of e-commerce order data.
-- =============================================================================
-- Idempotent: safe to re-run on a fresh database.

DROP TABLE IF EXISTS fact_order_items CASCADE;
DROP TABLE IF EXISTS dim_user         CASCADE;
DROP TABLE IF EXISTS dim_product      CASCADE;
DROP TABLE IF EXISTS dim_date         CASCADE;
DROP SEQUENCE IF EXISTS dim_user_seq;
DROP SEQUENCE IF EXISTS dim_product_seq;

-- -----------------------------------------------------------------------------
-- DIM_DATE
-- Stores pre-computed calendar attributes for fast GROUP BY (year, quarter, month).
-- Populated by the ETL using generate_series().
-- date_sk is an integer in YYYYMMDD format (e.g., 20231025).
-- -----------------------------------------------------------------------------
CREATE TABLE dim_date (
    date_sk    INTEGER      PRIMARY KEY,   -- Surrogate Key: YYYYMMDD integer
    full_date  DATE         NOT NULL,
    year       INTEGER      NOT NULL,
    month      INTEGER      NOT NULL,
    month_name VARCHAR(20)  NOT NULL,
    day        INTEGER      NOT NULL
);

-- -----------------------------------------------------------------------------
-- DIM_USER — SCD Type 2
-- Each row represents one VERSION of a user's attributes.
-- When a tracked attribute changes (e.g. address), the old row is expired and
-- a new row is inserted, preserving full historical accuracy.
--
-- user_sk   : Surrogate Key — uniquely identifies this specific version of the user.
-- user_id   : Natural/Business Key — the original ID from the source OLTP system.
-- start_date: When this version of the record became active.
-- end_date  : When this version was superseded (NULL = currently active).
-- is_current: Quick boolean flag to identify the active record without date math.
-- -----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS dim_user_seq START 1;
CREATE TABLE dim_user (
    user_sk    INTEGER      PRIMARY KEY DEFAULT nextval('dim_user_seq'),  -- Surrogate Key
    user_id    INTEGER      NOT NULL,        -- Natural Key (from source)
    name       VARCHAR(255),
    email      VARCHAR(255),
    address    VARCHAR(255),
    start_date TIMESTAMP    NOT NULL,        -- SCD Type 2: record effective from
    end_date   TIMESTAMP,                    -- SCD Type 2: record expired on (NULL = active)
    is_current BOOLEAN      NOT NULL         -- SCD Type 2: TRUE = currently active record
);

-- -----------------------------------------------------------------------------
-- DIM_PRODUCT — SCD Type 1 (overwrite)
-- Simple product dimension. Uses surrogate keys.
-- product_sk : Surrogate Key assigned by the data warehouse.
-- product_id : Natural Key from source system.
-- -----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS dim_product_seq START 1;
CREATE TABLE dim_product (
    product_sk   INTEGER        PRIMARY KEY DEFAULT nextval('dim_product_seq'),
    product_id   INTEGER        NOT NULL,
    product_name VARCHAR(255)   NOT NULL,
    category     VARCHAR(255),
    price        DECIMAL(10, 2) NOT NULL
);

-- -----------------------------------------------------------------------------
-- FACT_ORDER_ITEMS
-- Central fact table. Grain: one row = one line item within one order.
-- Contains foreign keys (surrogate) to all three dimensions + numeric measures.
-- order_item_id is the natural key retained for source traceability.
-- -----------------------------------------------------------------------------
CREATE TABLE fact_order_items (
    order_item_id INTEGER        PRIMARY KEY,   -- Natural Key (traceability)
    user_sk       INTEGER,                      -- FK -> dim_user (surrogate)
    product_sk    INTEGER,                      -- FK -> dim_product (surrogate)
    date_sk       INTEGER,                      -- FK -> dim_date (surrogate)
    quantity      INTEGER        NOT NULL,
    line_total    DECIMAL(10,2)  NOT NULL,
    CONSTRAINT fk_fact_user    FOREIGN KEY (user_sk)    REFERENCES dim_user(user_sk),
    CONSTRAINT fk_fact_product FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
    CONSTRAINT fk_fact_date    FOREIGN KEY (date_sk)    REFERENCES dim_date(date_sk)
);