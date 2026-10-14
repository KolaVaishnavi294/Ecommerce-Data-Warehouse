# Dimensional Data Warehouse & ETL Pipeline

A complete, production-quality data warehouse implementation that transforms a normalized e-commerce OLTP database (3NF) into a dimensional Star Schema, with a fully idempotent ETL pipeline featuring **Slowly Changing Dimensions Type 2 (SCD Type 2)** for historical user tracking.

---

## Project Overview

This project demonstrates the two worlds of database design:

| Aspect | OLTP (Source) | OLAP (Data Warehouse) |
|---|---|---|
| **Goal** | Fast transactions | Fast analytics |
| **Structure** | 3NF Normalized | Star Schema Denormalized |
| **Workload** | INSERT / UPDATE / DELETE | Complex SELECT with aggregations |
| **Tables** | users, products, orders, order_items | fact_order_items + 3 dimensions |

---

## Architecture

### Source System — 3NF Schema

```
users ──────────────┐
                    │ 1:N
                 orders
                    │ 1:N
                 order_items
                    │ N:1
products ───────────┘
```

### Data Warehouse — Star Schema

```
             dim_user (SCD Type 2)
                    │
                    │ user_sk
                    │
dim_date ─────── fact_order_items ─────── dim_product
 date_sk                                   product_sk
```

The fact table sits at the centre. Every dimension connects via **Surrogate Keys** (not natural keys), allowing full historical tracking.

---

## Entity-Relationship Diagrams

| Schema | File |
|---|---|
| Source OLTP (3NF) | `diagrams/3nf_schema.png` |
| Data Warehouse (Star Schema) | `diagrams/star_schema.png` |

---

## Project Structure

```
Ecommerce-Data-Warehouse/
│
├── README.md                    # This file
├── generate_data.py             # Python: generates synthetic 03_source_data.sql
├── generate_png_diagrams.py     # Python: generates ERD PNG diagrams
├── run_pipeline.py              # Python: end-to-end test runner (DuckDB)
│
├── diagrams/
│   ├── 3nf_schema.png           # 3NF ERD
│   └── star_schema.png          # Star Schema ERD
│
└── sql/
    ├── 01_source_ddl.sql        # Creates 3NF OLTP tables
    ├── 02_warehouse_ddl.sql     # Creates Star Schema DW tables
    ├── 03_source_data.sql       # Populates OLTP with 100 users, 50 products, 500 orders
    └── 04_etl.sql               # Idempotent ETL: dim_date, dim_product, dim_user (SCD2), fact
```

---

## Prerequisites

- **PostgreSQL 13+** (recommended) — or **DuckDB** for quick local testing
- No application dependencies required — pure SQL

---

## Execution Order

Run these scripts **sequentially** on a fresh, empty database:

### PostgreSQL

```bash
# Create a fresh database
createdb ecom_dw

# Step 1: Create 3NF source tables
psql -d ecom_dw -f sql/01_source_ddl.sql

# Step 2: Create Star Schema warehouse tables
psql -d ecom_dw -f sql/02_warehouse_ddl.sql

# Step 3: Populate source tables with synthetic data
psql -d ecom_dw -f sql/03_source_data.sql

# Step 4: Run the full ETL pipeline
psql -d ecom_dw -f sql/04_etl.sql
```

### DuckDB (One-Command Local Test)

```bash
python run_pipeline.py
```

This runs all 4 scripts, validates row counts, and automatically simulates + verifies SCD Type 2.

---

## Database Design

### Source Tables (3NF)

| Table | Key Columns | Purpose |
|---|---|---|
| `users` | `user_id PK` | Customer accounts |
| `products` | `product_id PK` | Product catalogue |
| `orders` | `order_id PK`, `user_id FK` | Customer orders |
| `order_items` | `order_item_id PK`, `order_id FK`, `product_id FK` | Individual line items |

### Warehouse Tables (Star Schema)

| Table | Key Columns | Purpose |
|---|---|---|
| `dim_date` | `date_sk PK` (YYYYMMDD integer) | Calendar dimension |
| `dim_product` | `product_sk PK`, `product_id` (natural key) | Product dimension |
| `dim_user` | `user_sk PK`, `user_id` (natural key), `start_date`, `end_date`, `is_current` | User dimension (SCD Type 2) |
| `fact_order_items` | `order_item_id PK`, `user_sk FK`, `product_sk FK`, `date_sk FK` | Central fact table |

---

## ETL Workflow

```
 Source 3NF Tables
        │
        ▼
 STEP 1: dim_date     ← generate_series() over 2020-2030
        │
        ▼
 STEP 2: dim_product  ← INSERT WHERE NOT EXISTS (idempotent)
        │
        ▼
 STEP 3: dim_user     ← SCD Type 2 logic (expire + insert)
        │
        ▼
 STEP 4: fact_order_items ← Surrogate key lookups + temporal join
```

---

## SCD Type 2 Explanation

### Problem
A user may change their address over time. If we simply overwrite the old address, all historical orders will incorrectly show the new address — destroying analytical accuracy.

### Solution: SCD Type 2
Instead of overwriting, we **add a new row** for each change and **expire the old one**.

| Column | Purpose |
|---|---|
| `user_sk` | Unique surrogate key for this specific version |
| `user_id` | Natural key — same across all versions |
| `start_date` | When this version became active |
| `end_date` | When this version was superseded (`NULL` = currently active) |
| `is_current` | `TRUE` for the active record |

### Flow
```
Source user address changes
        │
        ▼
  Compare against dim_user WHERE is_current = TRUE
        │
  ┌─────┴─────┐
  │           │
 No change  Changed
  │           │
  └─ Skip     ├─► UPDATE old row: is_current=FALSE, end_date=NOW
              │
              └─► INSERT new row: is_current=TRUE, start_date=NOW
```

### Temporal Fact Table Join
When loading `fact_order_items`, we join `dim_user` using a **temporal condition**:

```sql
JOIN dim_user du
  ON  o.user_id     = du.user_id
  AND o.order_date >= du.start_date
  AND (o.order_date < du.end_date OR du.end_date IS NULL)
```

This guarantees every order links to the address the customer had **at the time of purchase**.

---

## Validation Queries

Run these after executing `04_etl.sql` to verify correctness:

```sql
-- Row counts
SELECT COUNT(*) FROM users;           -- Should be 100
SELECT COUNT(*) FROM products;        -- Should be 50
SELECT COUNT(*) FROM orders;          -- Should be 500

SELECT COUNT(*) FROM dim_user;        -- Should be 100 (initial load)
SELECT COUNT(*) FROM dim_product;     -- Should be 50
SELECT COUNT(*) FROM dim_date;        -- Should be 4018 (2020-2030)
SELECT COUNT(*) FROM fact_order_items;-- Should be ~1000+

-- Verify no duplicate active records in dim_user
SELECT user_id, COUNT(*)
FROM dim_user
WHERE is_current = TRUE
GROUP BY user_id
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Verify all fact rows have valid surrogate keys
SELECT COUNT(*) FROM fact_order_items WHERE user_sk IS NULL;    -- Expected: 0
SELECT COUNT(*) FROM fact_order_items WHERE product_sk IS NULL; -- Expected: 0
SELECT COUNT(*) FROM fact_order_items WHERE date_sk IS NULL;    -- Expected: 0
```

---

## SCD Type 2 Verification Test

```sql
-- Step 1: Simulate address change
UPDATE users SET address = '999 New Avenue, Hyderabad' WHERE user_id = 1;

-- Step 2: Re-run ETL
-- (execute 04_etl.sql again)

-- Step 3: Verify two records for user_id = 1
SELECT user_sk, user_id, address, start_date, end_date, is_current
FROM dim_user
WHERE user_id = 1
ORDER BY start_date;
```

**Expected Output:**

| user_sk | user_id | address | is_current | end_date |
|---|---|---|---|---|
| 1 | 1 | 1 Main St, City 1 | FALSE | 2026-07-15 18:48:39 |
| 101 | 1 | 999 New Avenue, Hyderabad | TRUE | NULL |

---

## Expected Output After Initial ETL Run

| Table | Expected Rows |
|---|---|
| `users` | 100 |
| `products` | 50 |
| `orders` | 500 |
| `order_items` | ~1,000+ |
| `dim_user` | 100 |
| `dim_product` | 50 |
| `dim_date` | 4,018 |
| `fact_order_items` | ~1,000+ |
