"""
Notion Setup Script: Creates the Job Search OS database in Notion.
"""
import os
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables from .env
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")

if not NOTION_API_KEY or NOTION_API_KEY == "your_notion_api_key_here":
    print("Error: Please set your NOTION_API_KEY in the .env file.")
    exit(1)

# Initialize Notion client
notion = Client(auth=NOTION_API_KEY)

def setup_notion_db():
    print("Searching for 'Personal Home' page...")
    try:
        # 1. Search for the "Personal Home" page
        search_results = notion.search(
            query="Personal Home",
            filter={"property": "object", "value": "page"}
        ).get("results", [])

        if not search_results:
            print("Error: Could not find a page named 'Personal Home'. Please ensure it's shared with your integration.")
            return

        parent_page_id = search_results[0]["id"]
        print(f"Found 'Personal Home' page with ID: {parent_page_id}")

        # 2. Create the "Job Search OS" database
        print("Creating 'Job Search OS' database...")
        new_db = notion.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": "Job Search OS"}}],
            properties={
                "Name": {"title": {}},
                "Company": {"rich_text": {}},
                "URL": {"url": {}},
                "Score": {"number": {"format": "number"}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "New", "color": "blue"},
                            {"name": "Applied", "color": "yellow"},
                            {"name": "Interview", "color": "orange"},
                            {"name": "Rejected", "color": "red"},
                            {"name": "Offer", "color": "green"}
                        ]
                    }
                },
                "Applied At": {"date": {}},
                "Notes": {"rich_text": {}}
            }
        )

        db_id = new_db["id"]
        print(f"Success! 'Job Search OS' database created with ID: {db_id}")
        return db_id

    except Exception as e:
        print(f"An error occurred while setting up Notion: {e}")
        return None

if __name__ == "__main__":
    setup_notion_db()
