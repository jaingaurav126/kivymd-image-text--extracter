import sqlite3

# Define the database connection
conn = sqlite3.connect('invoice_data.db')
cursor = conn.cursor()

# List of tables to clear
tables = [
    'shop_address',
    'billing_address',
    'product',
    'total_bill',
    'invoice'
]

# Delete all records from each table
for table in tables:
    cursor.execute(f'DELETE FROM {table}')
    print(f'All records deleted from {table}.')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("All records from all tables have been deleted.")
