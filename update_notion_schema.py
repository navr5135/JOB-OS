"""
Update Notion Schema: Adds missing properties to the Notion database.
"""
import os
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    print("Error: Missing credentials in .env")
    exit(1)

notion = Client(auth=NOTION_API_KEY.strip())

def update_schema():
    print(f"Retrieving database {NOTION_DATABASE_ID}...")
    try:
        db_obj = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        
        # Identify the data source to update
        data_sources = db_obj.get("data_sources", [])
        if not data_sources:
            print("Error: No data sources found for this database. Schema update not possible with this method.")
            return
            
        ds_id = data_sources[0]["id"]
        print(f"Found data source: {ds_id}. Updating properties...")
        
        # Add missing properties
        # In this API version, we update the data_source
        notion.data_sources.update(
            data_source_id=ds_id,
            properties={
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
        
        print("Success! Properties added to the data source.")
        
    except Exception as e:
        print(f"Failed to update schema: {e}")

if __name__ == "__main__":
    update_schema()
