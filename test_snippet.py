import os
import mysql.connector
import hashlib

DB_PASSWORD = "admin123"

def connect_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=DB_PASSWORD,
        database="shop"
    )
    return conn

def get_user_by_name(username):
    conn = connect_db()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    result = cursor.fetchone()
    return result

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def find_duplicate_orders(orders):
    duplicates = []
    for i in range(len(orders)):
        for j in range(i + 1, len(orders)):
            if orders[i]['id'] == orders[j]['id']:
                duplicates.append(orders[i])
    return duplicates

def calculate_total(items):
    total = 0
    for item in items:
        total = total + item['price'] * item['qty']
    return total

def apply_discount(total, code):
    discount = 0
    if code == "SAVE10":
        discount = 10
    elif code == "SAVE20":
        discount = 20
    else:
        discount = 0
    final = total - (total * discount / 100)
    return final

def process_order(username, items, discount_code):
    user = get_user_by_name(username)
    if user == None:
        print("User not found")
        return
    total = calculate_total(items)
    final_total = apply_discount(total, discount_code)
    print("Order total for " + username + ": " + str(final_total))

    try:
        conn = connect_db()
        cursor = conn.cursor()
        query = "INSERT INTO orders (username, total) VALUES ('" + username + "', " + str(final_total) + ")"
        cursor.execute(query)
        conn.commit()
    except:
        pass

def get_all_products():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    result = []
    for p in products:
        result.append(p)
    return result

def search_products(keyword):
    products = get_all_products()
    matches = []
    for p in products:
        if keyword.lower() in p[1].lower():
            matches.append(p)
    return matches

def print_receipt(username, items, total):
    print("=====================")
    print("Receipt for: " + username)
    for item in items:
        print(item['name'] + " x" + str(item['qty']) + " = " + str(item['price'] * item['qty']))
    print("Total: " + str(total))
    print("=====================")

def main():
    sample_items = [
        {"name": "Laptop", "price": 50000, "qty": 1},
        {"name": "Mouse", "price": 500, "qty": 2}
    ]
    process_order("admin", sample_items, "SAVE10")
    products = search_products("lap")
    for p in products:
        print(p)

if __name__ == "__main__":
    main()