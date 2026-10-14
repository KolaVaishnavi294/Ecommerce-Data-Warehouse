-- sql/01_source_ddl.sql
-- =============================================================================
-- SOURCE OLTP SCHEMA — Third Normal Form (3NF)
-- E-Commerce transactional database
-- =============================================================================
-- Idempotent: safe to run on a fresh or existing database.
-- CASCADE ensures child tables are dropped before parent tables.

DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- -----------------------------------------------------------------------------
-- USERS
-- Stores registered customer accounts.
-- 'address' is the key attribute tracked historically via SCD Type 2 in the DW.
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    user_id    INTEGER      PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255) UNIQUE NOT NULL,
    address    VARCHAR(255),
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- PRODUCTS
-- Product catalog. Normalized so that a price update affects one row only.
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    product_id INTEGER      PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    category   VARCHAR(255),
    price      DECIMAL(10, 2) NOT NULL
);

-- -----------------------------------------------------------------------------
-- ORDERS
-- One row per customer order.
-- user_id FK enforces that every order belongs to a registered user.
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    order_id   INTEGER   PRIMARY KEY,
    user_id    INTEGER   NOT NULL,
    order_date TIMESTAMP NOT NULL,
    CONSTRAINT fk_orders_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- -----------------------------------------------------------------------------
-- ORDER_ITEMS
-- Resolves the many-to-many between orders and products.
-- One row per line item on an order — this is also the grain of our fact table.
-- -----------------------------------------------------------------------------
CREATE TABLE order_items (
    order_item_id INTEGER        PRIMARY KEY,
    order_id      INTEGER        NOT NULL,
    product_id    INTEGER        NOT NULL,
    quantity      INTEGER        NOT NULL CHECK (quantity > 0),
    total_price   DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
);