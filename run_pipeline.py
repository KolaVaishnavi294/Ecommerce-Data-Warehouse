"""
run_pipeline.py
---------------
Executes the full Data Warehouse ETL pipeline using DuckDB (in-process).
Creates a local file: ecommerce_warehouse.duckdb

Usage:
    python run_pipeline.py

It will:
  1. Run 01_source_ddl.sql   – Create 3NF source tables
  2. Run 02_warehouse_ddl.sql – Create Star Schema tables
  3. Run 03_source_data.sql   – Load synthetic source data
  4. Run 04_etl.sql           – Run ETL pipeline (SCD Type 2)
  5. Print row count validation results
  6. Simulate an address change and re-run ETL to prove SCD Type 2 works
"""

import duckdb
import os

DB_FILE = "ecommerce_warehouse.duckdb"
SQL_DIR = "sql"

SCRIPTS = [
    "01_source_ddl.sql",
    "02_warehouse_ddl.sql",
    "03_source_data.sql",
    "04_etl.sql",
]

def run_script(conn, script_name):
    path = os.path.join(SQL_DIR, script_name)
    print(f"\n{'='*60}")
    print(f"  Running: {script_name}")
    print(f"{'='*60}")
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.execute(sql)
    print(f"  [OK] {script_name} completed successfully.")

def print_counts(conn):
    print("\n" + "="*60)
    print("  ROW COUNT VALIDATION")
    print("="*60)
    tables = [
        ("users",           "Source OLTP: users"),
        ("products",        "Source OLTP: products"),
        ("orders",          "Source OLTP: orders"),
        ("order_items",     "Source OLTP: order_items"),
        ("dim_user",        "DW Dimension: dim_user"),
        ("dim_product",     "DW Dimension: dim_product"),
        ("dim_date",        "DW Dimension: dim_date"),
        ("fact_order_items","DW Fact: fact_order_items"),
    ]
    for table, label in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {label:<35}  {count:>6} rows")

def verify_scd2(conn):
    print("\n" + "="*60)
    print("  SCD TYPE 2 VERIFICATION")
    print("="*60)
    result = conn.execute("""
        SELECT user_sk, user_id, name, address, start_date, end_date, is_current
        FROM dim_user
        WHERE user_id = 1
        ORDER BY start_date
    """).fetchall()
    print(f"\n  Records for user_id = 1 in dim_user:")
    print(f"  {'user_sk':<10} {'user_id':<10} {'name':<15} {'address':<25} {'is_current':<12} {'end_date'}")
    print(f"  {'-'*90}")
    for row in result:
        print(f"  {str(row[0]):<10} {str(row[1]):<10} {str(row[2]):<15} {str(row[3]):<25} {str(row[6]):<12} {str(row[5])}")
    if len(result) == 2 and any(r[6] == False for r in result) and any(r[6] == True for r in result):
        print("\n  [PASS] SCD Type 2 PASSED: Old record expired, new record inserted!")
    elif len(result) == 1:
        print("\n  [INFO] Only one record found (SCD simulation not yet run).")
    else:
        print("\n  [WARN] Unexpected SCD state. Check ETL logic.")

def main():
    # Remove old DB file for a clean run
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"  [CLEAN] Removed old database: {DB_FILE}")

    conn = duckdb.connect(DB_FILE)

    # --- INITIAL PIPELINE RUN ---
    for script in SCRIPTS:
        run_script(conn, script)

    print_counts(conn)
    verify_scd2(conn)

    # --- SCD TYPE 2 SIMULATION ---
    print("\n" + "="*60)
    print("  SCD TYPE 2 SIMULATION")
    print("  Changing address of user_id=1 in source, then re-running ETL")
    print("="*60)
    conn.execute("UPDATE users SET address = '999 New Avenue, Hyderabad' WHERE user_id = 1")
    print("  [OK]  Updated address of user_id=1 in source 'users' table.")

    run_script(conn, "04_etl.sql")
    verify_scd2(conn)

    print("\n" + "="*60)
    print("  PIPELINE COMPLETE -- Data Warehouse is fully loaded!")
    print("="*60 + "\n")

    conn.close()

if __name__ == "__main__":
    main()
