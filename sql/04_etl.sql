-- sql/04_etl.sql
-- =============================================================================
-- ETL PIPELINE: Extract -> Transform -> Load
-- Moves data from the 3NF source tables into the Star Schema.
-- Compatible with DuckDB and PostgreSQL.
-- IDEMPOTENT: Running this script multiple times produces correct results.
-- =============================================================================

-- =============================================================================
-- STEP 1: POPULATE DIM_DATE
-- Generates a calendar dimension covering 2020-01-01 to 2030-12-31.
-- Uses generate_series() to create one row per calendar day.
-- The date_sk is an integer YYYYMMDD key (e.g. 20231025) for fast joins.
-- 'WHERE NOT IN' makes this idempotent: skips dates already loaded.
-- =============================================================================
INSERT INTO dim_date (date_sk, full_date, year, month, month_name, day)
SELECT
    CAST(strftime(datum, '%Y%m%d') AS INTEGER)  AS date_sk,
    datum::DATE                                  AS full_date,
    YEAR(datum)                                  AS year,
    MONTH(datum)                                 AS month,
    strftime(datum, '%B')                        AS month_name,
    DAY(datum)                                   AS day
FROM (
    SELECT UNNEST(generate_series(
        '2020-01-01'::TIMESTAMP,
        '2030-12-31'::TIMESTAMP,
        INTERVAL '1 day'
    )) AS datum
) dates
WHERE CAST(strftime(datum, '%Y%m%d') AS INTEGER)
      NOT IN (SELECT date_sk FROM dim_date);

-- =============================================================================
-- STEP 2: POPULATE DIM_PRODUCT (SCD Type 1 — Insert only)
-- Assigns a new surrogate key to any product not yet in the dimension.
-- 'WHERE NOT EXISTS' prevents duplicate inserts on re-run.
-- =============================================================================
INSERT INTO dim_product (product_id, product_name, category, price)
SELECT
    s.product_id,
    s.name        AS product_name,
    s.category,
    s.price
FROM products s
WHERE NOT EXISTS (
    SELECT 1
    FROM   dim_product d
    WHERE  d.product_id = s.product_id
);

-- =============================================================================
-- STEP 3: SCD TYPE 2 — DIM_USER
--
-- ALGORITHM:
--   Phase A (Detect)  : Find source users whose tracked attributes differ
--                       from their currently-active warehouse record.
--   Phase B (Expire)  : Mark those active records as historical
--                       (is_current = FALSE, end_date = now).
--   Phase C (Insert)  : Insert new rows for:
--                         (a) Brand-new users not yet in dim_user.
--                         (b) Changed users whose old record was just expired.
--
-- TEMPORAL ACCURACY:
--   Because dim_user stores start_date/end_date per version, the fact table
--   can join on order_date BETWEEN start_date AND end_date to guarantee that
--   every historical order references the address the customer had AT THAT TIME.
-- =============================================================================

-- Phase B: Expire old records where tracked attributes have changed
-- IS DISTINCT FROM handles NULL comparisons safely.
UPDATE dim_user
SET
    is_current = FALSE,
    end_date   = CURRENT_TIMESTAMP
FROM users s
WHERE dim_user.user_id    = s.user_id
  AND dim_user.is_current = TRUE
  AND (
        dim_user.name    IS DISTINCT FROM s.name    OR
        dim_user.email   IS DISTINCT FROM s.email   OR
        dim_user.address IS DISTINCT FROM s.address
      );

-- Phase C: Insert users with no currently-active record in the warehouse
-- This covers both NEW users and users whose record was just expired above.
INSERT INTO dim_user (user_id, name, email, address, start_date, end_date, is_current)
SELECT
    s.user_id,
    s.name,
    s.email,
    s.address,
    CURRENT_TIMESTAMP AS start_date,
    NULL              AS end_date,
    TRUE              AS is_current
FROM users s
WHERE NOT EXISTS (
    SELECT 1
    FROM   dim_user d
    WHERE  d.user_id    = s.user_id
      AND  d.is_current = TRUE
);

-- =============================================================================
-- STEP 4: POPULATE FACT_ORDER_ITEMS
--
-- KEY DESIGN POINTS:
--   1. Surrogate Key Lookup: We join on business keys to fetch the correct
--      surrogate keys (user_sk, product_sk, date_sk).
--
--   2. Temporal Integrity for dim_user:
--      The JOIN condition uses o.order_date >= du.start_date AND
--      (o.order_date < du.end_date OR du.end_date IS NULL).
--      This ensures we link each order to the EXACT user address that was
--      active when the order was placed — preserving historical accuracy.
--
--   3. LEFT JOIN usage: Prevents rows being silently dropped if a product
--      or user is missing from the dimension (defensively handles data gaps).
--
--   4. Idempotency: 'WHERE NOT EXISTS' skips order items already loaded.
-- =============================================================================
INSERT INTO fact_order_items
    (order_item_id, user_sk, product_sk, date_sk, quantity, line_total)
SELECT
    oi.order_item_id,
    du.user_sk,
    dp.product_sk,
    CAST(strftime(o.order_date, '%Y%m%d') AS INTEGER) AS date_sk,
    oi.quantity,
    oi.total_price                                     AS line_total
FROM order_items oi
JOIN   orders      o   ON  oi.order_id   = o.order_id
-- Temporal join: match the user version active at the time of the order
LEFT JOIN dim_user du
    ON  o.user_id      = du.user_id
    AND o.order_date  >= du.start_date
    AND (o.order_date  < du.end_date OR du.end_date IS NULL)
LEFT JOIN dim_product dp
    ON  oi.product_id  = dp.product_id
WHERE NOT EXISTS (
    SELECT 1
    FROM   fact_order_items f
    WHERE  f.order_item_id = oi.order_item_id
);