import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
          'https://www.googleapis.com/auth/drive.file']

class SheetsHandler:
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate and create Google Sheets service"""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', 
                 SCOPES
            )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('sheets', 'v4', credentials=creds)
    
    def create_new_tab(self, tab_name):
        """Create a new tab/sheet in the spreadsheet"""
        try:
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': tab_name
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=request_body
            ).execute()
            
            return response
        except Exception as e:
            print(f"Error creating tab: {e}")
            return None
    
    def write_headers(self, tab_name):
        """Write column headers to the new tab"""
        headers = [
            'Name', 'Address', 'City', 'State', 'Zip', 
            'Phone', 'Website', 'Email', 'Facebook', 
            'Instagram', 'LinkedIn', 'Twitter', 'Place ID'
        ]
        
        range_name = f"{tab_name}!A1:M1"
        
        body = {
            'values': [headers]
        }
        
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format headers (bold)
            self.format_headers(tab_name)
            
            return True
        except Exception as e:
            print(f"Error writing headers: {e}")
            return False
    
    def format_headers(self, tab_name):
        """Make headers bold"""
        try:
            # Get sheet ID by name
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == tab_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.textFormat.bold'
                }
            }]
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=body
            ).execute()
            
        except Exception as e:
            print(f"Error formatting headers: {e}")
    
    def write_data(self, tab_name, data):
        """Write lead data to the sheet"""
        if not data:
            return False
        
        # Convert data to rows
        rows = []
        for lead in data:
            row = [
                lead.get('name', ''),
                lead.get('address', ''),
                lead.get('city', ''),
                lead.get('state', ''),
                lead.get('zip', ''),
                lead.get('phone', ''),
                lead.get('website', ''),
                lead.get('email', ''),
                lead.get('facebook', ''),
                lead.get('instagram', ''),
                lead.get('linkedin', ''),
                lead.get('twitter', ''),
                lead.get('place_id', '')
            ]
            rows.append(row)
        
        range_name = f"{tab_name}!A2"  # Start at row 2 (after headers)
        
        body = {
            'values': rows
        }
        
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error writing data: {e}")
            return False
    
    def log_search_metadata(self, keyword, zipcode, radius, result_count, estimated_cost):
        """Log search info to Metadata tab"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            timestamp,
            keyword,
            zipcode,
            radius,
            result_count,
            f"${estimated_cost:.2f}",
            "Complete"
        ]
        
        # Check if Metadata tab exists, create if not
        try:
            range_name = "Metadata!A1"
            self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
        except:
            # Create Metadata tab and add headers
            self.create_new_tab("Metadata")
            headers = ['Timestamp', 'Keyword', 'Zipcode', 'Radius (mi)', 
                      'Results', 'Est. Cost', 'Status']
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range="Metadata!A1:G1",
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            self.format_headers("Metadata")
        
        # Append the search log
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range="Metadata!A2",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()
        except Exception as e:
            print(f"Error logging metadata: {e}")