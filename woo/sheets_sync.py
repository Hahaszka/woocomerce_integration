import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1PDwtpHnS6iLuxkbGixIPZxDubwJaIIlJHU7PPKMhBiM")
RANGE_NAME = os.getenv("GOOGLE_SHEET_RANGE", "Arkusz1!A:E")
SHEET_NAME = RANGE_NAME.split('!')[0] if '!' in RANGE_NAME else "Arkusz 1"

def get_sheets_service():
    creds = None
    # 1. Try Service Account (Preferred for Docker)
    if os.path.exists('service_account.json'):
        try:
            print("Found service_account.json, using Service Account authentication...")
            creds = service_account.Credentials.from_service_account_file(
                'service_account.json', scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)
            print("Google Sheets Service initialized successfully (Service Account).")
            return service
        except Exception as e:
            print(f"FAILED to initialize Service Account: {e}")

    # 2. Try User OAuth2
    if os.path.exists('token.json'):
        try:
            print("Found token.json, using User OAuth2 authentication...")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"FAILED to load token.json: {e}")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Token expired, refreshing...")
                creds.refresh(Request())
            except Exception as e:
                print(f"FAILED to refresh token: {e}")
        else:
            print("No valid Google credentials found (token.json or service_account.json).")
            return None
            
    try:
        service = build('sheets', 'v4', credentials=creds)
        print("Google Sheets Service initialized successfully (User OAuth2).")
        return service
    except Exception as e:
        print(f"FAILED to build Sheets service: {e}")
        return None

def sync_from_woo_to_sheets(wcapi):
    """Fetch everything from WooCommerce and overwrite the Sheet."""
    print("Syncing: WooCommerce -> Google Sheets...")
    service = get_sheets_service()
    if not service:
        print("Sync aborted: Google Sheets service not available.")
        return

    print("Fetching products from WooCommerce...")
    response = wcapi.get("products", params={"per_page": 100})
    if response.status_code != 200:
        print(f"ERROR: Failed to fetch products from WooCommerce (Status {response.status_code}): {response.text}")
        return
    
    products = response.json()
    print(f"Successfully fetched {len(products)} products from WooCommerce.")
    
    values = [['ID', 'Name', 'Price', 'Description', 'Image URLs']]
    for p in products:
        images = ", ".join([img['src'] for img in p.get('images', [])])
        desc = p.get('description', '').replace('<p>', '').replace('</p>', '').replace('<br />', '\n')
        values.append([
            str(p['id']),
            p['name'],
            str(p['regular_price']),
            desc,
            images
        ])

    try:
        print(f"Clearing Google Sheet (ID: {SHEET_ID}, Range: {RANGE_NAME})...")
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
        
        print(f"Updating Google Sheet with {len(values)-1} products...")
        body = {'values': values}
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID, range=RANGE_NAME,
            valueInputOption='RAW', body=body).execute()
        print("SUCCESS: WooCommerce -> Google Sheets sync completed.")
    except Exception as e:
        print(f"ERROR: Google Sheets API operation failed: {e}")

def sync_from_sheets_to_woo(wcapi):
    """Fetch everything from Sheets and update WooCommerce."""
    print("Syncing: Google Sheets -> WooCommerce...")
    service = get_sheets_service()
    if not service:
        print("Sync aborted: Google Sheets service not available.")
        return

    try:
        print(f"Fetching data from Google Sheet (ID: {SHEET_ID}, Range: {RANGE_NAME})...")
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
        rows = result.get('values', [])
    except Exception as e:
        print(f"ERROR: Failed to fetch data from Google Sheet: {e}")
        return
    
    if not rows or len(rows) <= 1:
        print("Google Sheet is empty or only contains headers. Nothing to sync to WooCommerce.")
        return
    
    data_rows = rows[1:]
    print(f"Processing {len(data_rows)} rows from Google Sheets...")
    
    updated_count = 0
    created_count = 0
    
    for i, row in enumerate(data_rows):
        while len(row) < 5:
            row.append("")
            
        p_id = row[0].strip() if row[0] else ""
        name = row[1].strip()
        price = row[2].strip()
        desc = row[3].strip()
        images_str = row[4].strip()
        
        if not name:
            continue
        
        images = [{"src": url.strip()} for url in images_str.split(",") if url.strip()]
        product_data = {
            "name": name,
            "regular_price": price,
            "description": desc,
            "images": images
        }
        
        try:
            if p_id:
                # Update existing
                res = wcapi.put(f"products/{p_id}", product_data)
                if res.status_code == 200:
                    updated_count += 1
                else:
                    print(f"WARNING: Failed to update product {p_id} in WooCommerce: {res.text}")
            else:
                # Create new
                res = wcapi.post("products", product_data)
                if res.status_code in [200, 201]:
                    new_p = res.json()
                    created_count += 1
                    # Update ID in Sheets (Column A)
                    row_index = i + 2
                    cell_range = f'{SHEET_NAME}!A{row_index}'
                    service.spreadsheets().values().update(
                        spreadsheetId=SHEET_ID, range=cell_range,
                        valueInputOption='RAW', body={'values': [[str(new_p['id'])]]}).execute()
                else:
                    print(f"WARNING: Failed to create product '{name}' in WooCommerce: {res.text}")
        except Exception as e:
            print(f"ERROR: WooCommerce API operation failed for row {i+2}: {e}")
                    
    print(f"SUCCESS: Sheets -> WooCommerce sync completed. (Created: {created_count}, Updated: {updated_count})")

def full_sync(wcapi):
    """Perform a full bidirectional sync."""
    print("--- STARTING FULL BIDIRECTIONAL SYNC ---")
    try:
        # 1. New items in Sheets -> WooCommerce
        sync_from_sheets_to_woo(wcapi)
        # 2. All items in WooCommerce -> Sheets
        sync_from_woo_to_sheets(wcapi)
        print("--- FULL SYNC COMPLETED SUCCESSFULLY ---")
    except Exception as e:
        print(f"--- FULL SYNC FAILED: {e} ---")
