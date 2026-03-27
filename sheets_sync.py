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
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Token expired, refreshing...")
                creds.refresh(Request())
            except Exception as e:
                print(f"FAILED to refresh token: {e}")
        else:
            print("No valid Google credentials found (service_account.json).")
            return None
            
    try:
        service = build('sheets', 'v4', credentials=creds)
        print("Google Sheets Service initialized successfully.")
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

def full_sync(wcapi):
    """Perform a full bidirectional sync."""
    print("--- STARTING FULL BIDIRECTIONAL SYNC ---")
    try:
        sync_from_woo_to_sheets(wcapi)
        print("--- FULL SYNC COMPLETED SUCCESSFULLY ---")
    except Exception as e:
        print(f"--- FULL SYNC FAILED: {e} ---")
