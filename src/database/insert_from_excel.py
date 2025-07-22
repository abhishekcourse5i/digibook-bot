import pandas as pd
import sqlite3
import argparse
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'digibook.db')

def insert_data_from_excel(table_name, excel_file):
    df = pd.read_excel(excel_file)
    # Convert all datetime columns to string to avoid sqlite3 binding errors
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
    # Convert all string values to lowercase
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.lower() if isinstance(x, str) else x)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Empty the table before inserting new data
    cursor.execute(f'DELETE FROM {table_name}')
    # Quote all column names to handle special characters
    columns = ', '.join([f'"{col}"' for col in df.columns])
    placeholders = ', '.join(['?'] * len(df.columns))
    insert_sql = f"INSERT OR IGNORE INTO {table_name} ({columns}) VALUES ({placeholders})"
    data = [tuple(row) for row in df.values]
    cursor.executemany(insert_sql, data)
    conn.commit()
    conn.close()
    print(f"Emptied and inserted {len(df)} rows into {table_name} from {excel_file}")

def main():
    parser = argparse.ArgumentParser(description='Insert data from Excel files into digibook.db tables.')
    parser.add_argument('--user', type=str, help='Path to Excel file for user table')
    parser.add_argument('--account', type=str, help='Path to Excel file for account table')
    parser.add_argument('--obm', type=str, help='Path to Excel file for obm table')
    args = parser.parse_args()

    if args.user:
        insert_data_from_excel('user', args.user)
    if args.account:
        insert_data_from_excel('account', args.account)
    if args.obm:
        insert_data_from_excel('obm', args.obm)
    if not (args.user or args.account or args.obm):
        print('No Excel files provided. Use --user, --account, or --obm to specify files.')

if __name__ == '__main__':
    main() 