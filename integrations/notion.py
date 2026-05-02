"""
Notion Integration: Syncs job listings between the local database and Notion.
"""
import os
import db
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Initialize Notion client
if NOTION_API_KEY:
    notion = Client(auth=NOTION_API_KEY.strip())
else:
    notion = None

# Status mapping: local_db_value -> Notion_select_value
STATUS_MAP = {
    "new": "New",
    "applied": "Applied",
    "interview": "Interview",
    "rejected": "Rejected",
    "offer": "Offer",
    "outreached": "Outreached"
}

def sync_job_to_notion(job):
    """Syncs a single job to the Notion database."""
    if not notion or not NOTION_DATABASE_ID:
        print("Notion client not initialized. Check .env file.")
        return False

    url = job.get('url')
    title = job.get('title', 'Unknown Title')
    company = job.get('company', 'Unknown Company')
    score = job.get('score', 0)
    status = STATUS_MAP.get(job.get('status', 'new'), "New")
    notes = job.get('notes', '') or ''

    try:
        # Search for page by URL (as query) and verify locally
        # 1. Check if job already exists by URL using search and local filter
        search_results = notion.search(
            query=url if url else title,
            filter={"property": "object", "value": "page"}
        ).get("results", [])

        page_id = None
        for result in search_results:
            # Verify database parent (handling both hyphenated and non-hyphenated IDs)
            parent = result.get("parent", {})
            db_parent_id = parent.get("database_id", "").replace("-", "")
            target_db_id = NOTION_DATABASE_ID.replace("-", "")
            
            if db_parent_id == target_db_id:
                props = result.get("properties", {})
                # Try to get URL from property (might be nested)
                remote_url = props.get("URL", {}).get("url")
                if remote_url == url:
                    page_id = result["id"]
                    break

        if page_id:
            # Update existing page
            notion.pages.update(
                page_id = page_id,
                properties = {
                    "Score": {"number": score},
                    "Status": {"select": {"name": status}},
                    "Notes": {"rich_text": [{"text": {"content": notes}}]}
                }
            )
            return "updated"
        else:
            # Create new page
            notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Company": {"rich_text": [{"text": {"content": company}}]},
                    "URL": {"url": url},
                    "Score": {"number": score},
                    "Status": {"select": {"name": status}},
                    "Notes": {"rich_text": [{"text": {"content": notes}}]}
                }
            )
            return "created"

    except Exception as e:
        print(f"Error syncing {title} to Notion: {e}")
        return False

def sync_all_jobs():
    """Fetches all jobs from local DB and syncs them to Notion."""
    jobs = db.get_all_jobs()
    created_count = 0
    updated_count = 0

    print(f"Syncing {len(jobs)} jobs to Notion...")
    
    for job in jobs:
        result = sync_job_to_notion(job)
        if result == "created":
            created_count += 1
        elif result == "updated":
            updated_count += 1

    print(f"Sync Summary: {created_count} created, {updated_count} updated.")

def update_notion_status(url, new_status):
    """Updates only the status of a job in Notion found by URL."""
    if not notion or not NOTION_DATABASE_ID:
        return

    status_val = STATUS_MAP.get(new_status, "New")

    try:
        search_results = notion.search(
            query=url,
            filter={"property": "object", "value": "page"}
        ).get("results", [])

        page_id = None
        for result in search_results:
            if result.get("parent", {}).get("database_id", "").replace("-", "") == NOTION_DATABASE_ID.replace("-", ""):
                if result.get("properties", {}).get("URL", {}).get("url") == url:
                    page_id = result["id"]
                    break

        if page_id:
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Status": {"select": {"name": status_val}}
                }
            )
            print(f"Updated Notion status to '{status_val}' for {url}")
    except Exception as e:
        print(f"Error updating Notion status: {e}")

if __name__ == "__main__":
    sync_all_jobs()
