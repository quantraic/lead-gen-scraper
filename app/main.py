import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from datetime import datetime

from .google_places import PlacesSearcher
from .scraper import WebsiteScraper
from .sheets_handler import SheetsHandler

# Load environment variables
load_dotenv()

app = FastAPI(title="Lead Gen Scraper")

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Initialize handlers
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main search form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/estimate")
async def estimate_cost(
    keyword: str = Form(...),
    zipcode: str = Form(...),
    radius: int = Form(...)
):
    """Estimate the cost of a search without running it"""
    try:
        places_searcher = PlacesSearcher(GOOGLE_PLACES_API_KEY)
        estimate = places_searcher.estimate_cost(radius)
        
        return {
            "success": True,
            "estimate": estimate
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/search")
async def run_search(
    keyword: str = Form(...),
    zipcode: str = Form(...),
    radius: int = Form(...),
    scrape_websites: bool = Form(False)
):
    """Run the lead generation search"""
    try:
        print(f"\n{'='*50}")
        print(f"Starting search: {keyword} | {zipcode} | {radius}mi")
        print(f"{'='*50}\n")
        
        # Initialize searcher
        places_searcher = PlacesSearcher(GOOGLE_PLACES_API_KEY)
        
        # Estimate cost
        estimate = places_searcher.estimate_cost(radius)
        print(f"Estimated cost: ${estimate['total_cost']:.2f}")
        print(f"Estimated results: {estimate['estimated_places']}")
        
        # Search Google Places
        print("\nSearching Google Places API...")
        leads = places_searcher.search_area(keyword, zipcode, radius)
        
        if not leads:
            return {
                "success": False,
                "error": "No results found"
            }
        
        print(f"\nFound {len(leads)} leads")
        
        # Scrape websites if requested
        if scrape_websites:
            print("\nScraping websites for emails and social links...")
            scraper = WebsiteScraper()
            leads = scraper.scrape_batch(leads, delay=1)
            
            # Count how many emails found
            emails_found = sum(1 for lead in leads if lead.get('email'))
            print(f"Found {emails_found} email addresses")
        
        # Write to Google Sheets
        print("\nWriting to Google Sheets...")
        sheets_handler = SheetsHandler(GOOGLE_SHEET_ID)
        
        # Create tab name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        tab_name = f"{keyword.replace(' ', '_')}_{zipcode}_{timestamp}"
        
        # Create new tab and write data
        sheets_handler.create_new_tab(tab_name)
        sheets_handler.write_headers(tab_name)
        sheets_handler.write_data(tab_name, leads)
        
        # Log metadata
        sheets_handler.log_search_metadata(
            keyword=keyword,
            zipcode=zipcode,
            radius=radius,
            result_count=len(leads),
            estimated_cost=estimate['total_cost']
        )
        
        print(f"\n{'='*50}")
        print(f"✓ Search complete! Check your Google Sheet.")
        print(f"✓ Tab name: {tab_name}")
        print(f"✓ Total leads: {len(leads)}")
        print(f"{'='*50}\n")
        
        return {
            "success": True,
            "results_count": len(leads),
            "tab_name": tab_name,
            "estimated_cost": estimate['total_cost'],
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        }
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}