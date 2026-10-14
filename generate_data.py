import random
from datetime import datetime, timedelta

def generate():
    with open('sql/03_source_data.sql', 'w') as f:
        f.write("-- sql/03_source_data.sql\n\n")
        
        # 100 users (include explicit user_id)
        f.write("INSERT INTO users (user_id, name, email, address, created_at) VALUES\n")
        users = []
        for i in range(1, 101):
            name = f"User {i}"
            email = f"user{i}@example.com"
            address = f"{i} Main St, City {i}"
            created_at = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 30))
            users.append(f"({i}, '{name}', '{email}', '{address}', '{created_at.strftime('%Y-%m-%d %H:%M:%S')}')")
        f.write(",\n".join(users) + ";\n\n")

        # 50 products (include explicit product_id)
        f.write("INSERT INTO products (product_id, name, category, price) VALUES\n")
        products = []
        categories = ["Electronics", "Clothing", "Home", "Books", "Toys"]
        for i in range(1, 51):
            name = f"Product {i}"
            category = random.choice(categories)
            price = round(random.uniform(10.0, 500.0), 2)
            products.append(f"({i}, '{name}', '{category}', {price})")
        f.write(",\n".join(products) + ";\n\n")

        # 500 orders (include explicit order_id)
        f.write("INSERT INTO orders (order_id, user_id, order_date) VALUES\n")
        orders = []
        for i in range(1, 501):
            user_id = random.randint(1, 100)
            order_date = datetime(2023, 2, 1) + timedelta(days=random.randint(0, 200))
            orders.append(f"({i}, {user_id}, '{order_date.strftime('%Y-%m-%d %H:%M:%S')}')")
        f.write(",\n".join(orders) + ";\n\n")

        # order_items (include explicit order_item_id)
        f.write("INSERT INTO order_items (order_item_id, order_id, product_id, quantity, total_price) VALUES\n")
        order_items = []
        item_id = 1
        for i in range(1, 501):
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                product_id = random.randint(1, 50)
                quantity = random.randint(1, 5)
                total_price = round(random.uniform(10.0, 500.0) * quantity, 2)
                order_items.append(f"({item_id}, {i}, {product_id}, {quantity}, {total_price})")
                item_id += 1
        f.write(",\n".join(order_items) + ";\n\n")

generate()
