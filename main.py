"""
Main entry point for Job Search OS. Initializes the application and starts the orchestrator.
"""
import orchestrator
import time
import sys
import threading
from integrations import telegram
import db

def print_banner():
    print("="*42)
    print("JOB SEARCH OS — RUNNING")
    print("Model: qwen3:8b (scoring) | qwen2.5:1.5b (writing)")
    print("="*42)

def main():
    print_banner()
    db.init_db()

    if '--once' in sys.argv:
        print("Running in --once mode for cloud/task scheduler.")
        orchestrator.run_now()
        sys.exit(0)
    
    # Start Telegram Listener Daemon
    t = threading.Thread(target=telegram.start_bot_listener, daemon=True)
    t.start()
    
    telegram.send_message("🚀 *Job Search OS is live!*\nCommands: /run /stop /status /jobs /help")
    
    # 1. Trigger the pipeline immediately on startup
    try:
        print("Daemon mode active. Telegram Bot is listening 24/7...")
        # Start the schedule loop (fires at 9:00 AM autonomously)
        orchestrator.start_scheduler()

        while True:
            import schedule
            schedule.run_pending()
            time.sleep(60) # Check every minute
            
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
