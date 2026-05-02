"""
Orchestrator: Runs all agents on a defined schedule and manages the execution flow.
"""
import schedule
import time
from datetime import datetime
import db
from agents.discovery import run_discovery
from agents.application import run_application
from integrations.notion import sync_all_jobs
from integrations import telegram

def get_timestamp():
    """Returns a formatted current timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _sync_notion():
    try:
        print(f"[{get_timestamp()}] >>> Starting Notion sync...")
        sync_all_jobs()
        print(f"[{get_timestamp()}] Notion sync complete.")
    except Exception as e:
        print(f"[{get_timestamp()}] Notion sync failed: {e}")

def run_discovery_only():
    print(f"\n[{get_timestamp()}] >>> Starting discovery-only run...")
    run_discovery()
    _sync_notion()
    telegram.send_report("Discovery Complete", {
        'saved': len(db.get_jobs_by_status("new")),
        'applications': 0,
        'runtime': 'single command'
    })

def run_application_only():
    print(f"\n[{get_timestamp()}] >>> Starting application-only run...")
    initial_applied_count = len(db.get_jobs_by_status("applied"))
    run_application()
    apps_generated = len(db.get_jobs_by_status("applied")) - initial_applied_count
    _sync_notion()
    telegram.send_report("Application Writing Complete", {
        'saved': len(db.get_jobs_by_status("new")),
        'applications': apps_generated,
        'runtime': 'single command'
    })

def run_pipeline():
    """Executes the complete job search pipeline."""
    start_time = time.time()
    try:
        telegram.send_message("🔍 Starting Job Search pipeline...")
    except Exception as e:
        print(f"Telegram start msg failed: {e}")
        
    print(f"\n[{get_timestamp()}] >>> Starting discovery...")
    
    # Get initial state for summary
    initial_applied_count = len(db.get_jobs_by_status("applied"))
    
    # 1. Run Discovery
    run_discovery()
    
    # Jobs ready for application writing after discovery.
    matched_jobs_count = len(db.get_jobs_by_status("new"))
    
    print(f"[{get_timestamp()}] Discovery finished. Waiting 5 seconds before writing applications...")
    time.sleep(5)
    
    print(f"[{get_timestamp()}] >>> Starting application writer...")
    
    # 2. Run Application Writer
    run_application()
    
    # Final state
    final_applied_count = len(db.get_jobs_by_status("applied"))
    apps_generated = final_applied_count - initial_applied_count
    
    print("\n" + "="*50)
    print("PIPELINE SUMMARY")
    print(f"[{get_timestamp()}]")
    remaining_new_count = len(db.get_jobs_by_status("new"))
    print(f"Jobs matched before application writing: {matched_jobs_count}")
    print(f"Jobs still in 'new' status: {remaining_new_count}")
    print(f"Applications generated in this run: {apps_generated}")
    print("="*50 + "\n")

    # 3. Sync to Notion
    _sync_notion()
        
    end_time = time.time()
    runtime_mins = round((end_time - start_time) / 60, 2)
    stats = {
        'saved': matched_jobs_count,
        'applications': apps_generated,
        'runtime': f"{runtime_mins} mins"
    }
    
    try:
        telegram.send_report("📊 Pipeline Complete", stats)
    except Exception as e:
        print(f"Telegram report failed: {e}")

def run_now(command="run"):
    """Triggers the pipeline immediately."""
    if command == "discover":
        run_discovery_only()
    elif command == "apply":
        run_application_only()
    elif command == "chat":
        from agents.chat_assistant import run_chat_once
        run_chat_once()
    else:
        run_pipeline()

def start_scheduler():
    """Sets up the daily schedule."""
    schedule.every().day.at("09:00").do(run_pipeline)
    print(f"[{get_timestamp()}] Pipeline scheduled for daily run at 09:00 AM.")
