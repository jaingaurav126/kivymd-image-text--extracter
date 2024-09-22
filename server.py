from flask import Flask, request, jsonify, send_file
import sqlite3
import base64
from pdf2image import convert_from_path
from PIL import Image
import openai
import instructor
from pydantic import BaseModel, Field
from typing import List
import pandas as pd
import xlsxwriter
from io import BytesIO  # Add this line
import os
import subprocess
import shutil
app = Flask(__name__)

# Initialize the OpenAI client
openaikey = ""
client = openai.OpenAI(api_key=openaikey)
uploads_dir = 'uploads'
# SQLite connection
def get_db_connection():
    conn = sqlite3.connect('invoice_data.db')
    return conn

# Create the necessary tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS shop_address (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        address_line TEXT,
                        city TEXT,
                        state_province_code TEXT,
                        postal_code INTEGER
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS billing_address (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        address_line TEXT,
                        city TEXT,
                        state_province_code TEXT,
                        postal_code INTEGER
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS product (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_description TEXT,
                        hsn TEXT,
                        count INTEGER,
                        unit_item_price REAL,
                        product_total_price REAL
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS total_bill (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        total REAL,
                        discount_amount REAL,
                        tax_amount REAL,
                        delivery_charges REAL,
                        final_total REAL
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS invoice (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_number TEXT,
                        shop_address_id INTEGER,
                        billing_address_id INTEGER,
                        total_bill_id INTEGER,
                        FOREIGN KEY (shop_address_id) REFERENCES shop_address(id),
                        FOREIGN KEY (billing_address_id) REFERENCES billing_address(id),
                        FOREIGN KEY (total_bill_id) REFERENCES total_bill(id)
                    )''')

    conn.commit()
    conn.close()

# Run at the start to create the tables
create_tables()

# Models for structured data
class Shop_Address(BaseModel):
    name: str
    address_line: str
    city: str
    state_province_code: str
    postal_code: int

class Address(BaseModel):
    name: str
    address_line: str
    city: str
    state_province_code: str
    postal_code: int

class Product(BaseModel):
    product_description: str
    hsn: str
    count: int
    unit_item_price: float
    product_total_price: float

class TotalBill(BaseModel):
    total: float
    discount_amount: float
    tax_amount: float
    delivery_charges: float
    final_total: float

class Invoice(BaseModel):
    invoice_number: str
    shop_address: Shop_Address
    billing_address: Address
    product: List[Product]
    total_bill: TotalBill

# Route for uploading the image
@app.route('/upload', methods=['POST'])
def upload_image():
    if os.path.exists(uploads_dir):
    # Remove all the contents of the uploads directory
        for filename in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)  # Remove file or symbolic link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory and all its contents
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        print(f'{uploads_dir} does not exist.')

    print("All contents of the uploads directory have been deleted.")
    # Get the image from the request
    image_data = request.data

    # Save the image temporarily
    with open("uploaded_image.jpg", "wb") as f:
        f.write(image_data)

    # Extract the data from the image (can be PDF as well)
    resume_image_path = 'uploaded_image.jpg'
    
    # Encode the image for OpenAI
    with open(resume_image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

    # Extract invoice data using OpenAI
    messages = [
        {"role": "user", "content": "Your goal is to extract structured information from the provided invoice"},
        {
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}]
        }
    ]

    response = instructor.from_openai(client).chat.completions.create(
        model='gpt-4o',
        response_model=Invoice,
        messages=messages
    )

    invoice_data = Invoice.parse_raw(response.model_dump_json())

    # Insert extracted data into the database
    insert_data_into_db(invoice_data.dict())

    table_names = ['shop_address', 'billing_address', 'product', 'total_bill', 'invoice']
    return jsonify({"message": "Data inserted successfully", "table_names": table_names})

# Function to insert data into SQLite
def insert_data_into_db(invoice_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert shop address
    cursor.execute('''
        INSERT INTO shop_address (name, address_line, city, state_province_code, postal_code)
        VALUES (?, ?, ?, ?, ?)''',
        (invoice_data["shop_address"]["name"],
         invoice_data["shop_address"]["address_line"],
         invoice_data["shop_address"]["city"],
         invoice_data["shop_address"]["state_province_code"],
         invoice_data["shop_address"]["postal_code"]))

    shop_address_id = cursor.lastrowid

    # Insert billing address
    cursor.execute('''
        INSERT INTO billing_address (name, address_line, city, state_province_code, postal_code)
        VALUES (?, ?, ?, ?, ?)''',
        (invoice_data["billing_address"]["name"],
         invoice_data["billing_address"]["address_line"],
         invoice_data["billing_address"]["city"],
         invoice_data["billing_address"]["state_province_code"],
         invoice_data["billing_address"]["postal_code"]))

    billing_address_id = cursor.lastrowid

    # Insert total bill
    cursor.execute('''
        INSERT INTO total_bill (total, discount_amount, tax_amount, delivery_charges, final_total)
        VALUES (?, ?, ?, ?, ?)''',
        (invoice_data["total_bill"]["total"],
         invoice_data["total_bill"]["discount_amount"],
         invoice_data["total_bill"]["tax_amount"],
         invoice_data["total_bill"]["delivery_charges"],
         invoice_data["total_bill"]["final_total"]))

    total_bill_id = cursor.lastrowid

    # Insert products
    for product in invoice_data["product"]:
        cursor.execute('''
            INSERT INTO product (product_description, hsn, count, unit_item_price, product_total_price)
            VALUES (?, ?, ?, ?, ?)''',
            (product["product_description"],
             product["hsn"],
             product["count"],
             product["unit_item_price"],
             product["product_total_price"]))

    # Insert invoice
    cursor.execute('''
        INSERT INTO invoice (invoice_number, shop_address_id, billing_address_id, total_bill_id)
        VALUES (?, ?, ?, ?)''',
        (invoice_data["invoice_number"],
         shop_address_id,
         billing_address_id,
         total_bill_id))

    conn.commit()
    conn.close()


"""@app.route('/data/<table_name>', methods=['GET'])
def get_table_data(table_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]

    conn.close()
    return jsonify({"columns": column_names, "data": rows})"""


@app.route('/download', methods=['GET'])
def download_data():
    # Path to save the Excel file
    output_path = os.path.join('uploads', 'data.xlsx')

    # Create an Excel workbook and worksheet
    workbook = xlsxwriter.Workbook(output_path)
    tables = ['shop_address', 'billing_address', 'product', 'total_bill', 'invoice']

    for table in tables:
        worksheet = workbook.add_worksheet(table)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        # Write column headers
        for col_num, column_title in enumerate(column_names):
            worksheet.write(0, col_num, column_title)

        # Write data rows
        for row_num, row in enumerate(rows, start=1):
            for col_num, cell_value in enumerate(row):
                worksheet.write(row_num, col_num, cell_value)

        conn.close()

    workbook.close()
    os.remove("uploaded_image.jpg")
    try:
        # This assumes ocr.py is in the same directory as this Flask app
        subprocess.run(['python', 'ocr.py'], check=True)
        print("ocr.py script executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing ocr.py: {e}")

    # Return the path to the saved Excel file
    return jsonify({
        "message": "Data exported successfully",
        "file_path": output_path
    })

if __name__ == "__main__":
    app.run(debug=True)