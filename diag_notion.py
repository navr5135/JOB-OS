import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

key = os.getenv("NOTION_API_KEY")
db_id = os.getenv("NOTION_DATABASE_ID")

print(f"Key preview: {key[:10]}...")
print(f"DB ID: '{db_id}'")

notion = Client(auth=key)

try:
    print("Testing databases.retrieve...")
    db_info = notion.databases.retrieve(database_id=db_id)
    print("DB Title:", db_info.get("title", [{}])[0].get("text", {}).get("content"))
    
    print("\nTesting databases.query (if it exists)...")
    if hasattr(notion.databases, "query"):
        print("databases.query exists!")
    else:
        print("databases.query DOES NOT exist!")
except Exception as e:
    print(f"Test failed: {e}")
