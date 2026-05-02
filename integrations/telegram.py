import os
import requests
import time
import sys
import threading
from dotenv import load_dotenv

# Allow loading db module safely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text: str):
    """Sends a markdown message to the Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram API warning: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Telegram network error: {e}")

def send_report(title: str, stats: dict):
    """Formats and sends a statistics report message to Telegram."""
    message = (
        f"*{title}*\n"
        f"📋 Jobs discovered: {stats.get('discovered', 0)}\n"
        f"✅ New matches saved: {stats.get('saved', 0)}\n"
        f"📝 Applications generated: {stats.get('applications', 0)}\n"
        f"📧 Cold emails sent: {stats.get('emails', 0)}\n"
        f"🕐 Run time: {stats.get('runtime', 'N/A')}"
    )
    send_message(message)

def start_bot_listener():
    """Polls Telegram API for commands and responds."""
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram Bot Token not configured. Listener disabled.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    offset = None
    first_run = True
    
    print("Telegram listener started...")
    
    while True:
        try:
            params = {"timeout": 10, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset
                
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("ok"):
                for result in data.get("result", []):
                    update_id = result.get("update_id")
                    offset = update_id + 1
                    
                    if first_run:
                        # Skip processing old commands currently stuck in the queue
                        continue
                    
                    message = result.get("message", {})
                    text = message.get("text", "").strip()
                    chat_id = str(message.get("chat", {}).get("id"))
                    
                    # Only map specified user
                    if chat_id != TELEGRAM_CHAT_ID:
                        continue
                        
                    if text == "/status":
                        send_message("✅ Agent is running. Next run: 9AM daily")
                        
                    elif text == "/run":
                        send_message("🚀 Executing manual orchestrator run...")
                        import orchestrator
                        t = threading.Thread(target=orchestrator.run_pipeline)
                        t.start()
                        
                    elif text == "/stop":
                        send_message("🛑 Shutting down...")
                        import os
                        os._exit(0)
                        
                    elif text == "/jobs":
                        try:
                            # Fetch top 5 recent jobs with status = 'new'
                            all_jobs = db.get_jobs_by_status('new')
                            recent = all_jobs[-5:] # Last 5
                            if not recent:
                                send_message("No new jobs in database.")
                            else:
                                msg = "*Top 5 New Jobs:*\n"
                                for j in reversed(recent):
                                    msg += f"- [{j['title']}]({j['url']}) @ {j['company']} (Score: {j['score']})\n"
                                send_message(msg)
                        except Exception as e:
                            send_message(f"Error fetching jobs: {e}")
                            
                    elif text == "/help":
                        send_message("🛠 *Job Search OS Commands*\n/run - Trigger full pipeline\n/stop - Shut down agent\n/status - Check status\n/jobs - View 5 recent matched jobs\n/email - Email yourself top 10 matches\n/report - Email full pipeline stats\n/apply - Show 5 top new jobs to apply to\n/help - Show this menu")

                    elif text == "/apply":
                        try:
                            import db
                            all_jobs = db.get_all_jobs()
                            new_jobs = [j for j in all_jobs if j.get('status') == 'new']
                            new_jobs.sort(key=lambda x: int(x.get('score') or 0), reverse=True)
                            top_5 = new_jobs[:5]
                            
                            if not top_5:
                                send_message("No 'new' jobs available to apply to.")
                            else:
                                msg = "🚀 *Top 5 New Jobs to Apply For:*\n\n"
                                for j in top_5:
                                    msg += f"👉 *{j['title']}* @ {j['company']}\n"
                                    msg += f"Score: {j.get('score')}\n{j['url']}\n\n"
                                send_message(msg)
                        except Exception as e:
                            send_message(f"Error fetching apply list: {e}")

                    elif text == "/report":
                        def send_report_worker():
                            try:
                                import config
                                import db
                                from integrations import gmail
                                
                                stats = db.get_database_stats()
                                total_jobs = sum(stats.values())
                                
                                all_jobs = db.get_all_jobs()
                                latest_run = max([j.get('created_at', '') for j in all_jobs]) if all_jobs else "Never"
                                
                                target_jobs = [j for j in all_jobs if j.get('status') in ('new', 'applied')]
                                target_jobs.sort(key=lambda x: int(x.get('score') or 0), reverse=True)
                                top_3 = target_jobs[:3]
                                
                                body_lines = [
                                    "Job Search OS — Pipeline Report\n",
                                    f"Total jobs in DB: {total_jobs}",
                                    f"Status Breakdown:",
                                    f"  - New: {stats.get('new', 0)}",
                                    f"  - Applied: {stats.get('applied', 0)}",
                                    f"  - Outreached: {stats.get('outreached', 0)}",
                                    f"  - Interview: {stats.get('interview', 0)}",
                                    f"\nLast job seen at: {latest_run}\n",
                                    "Top 3 Matches:"
                                ]
                                
                                for idx, j in enumerate(top_3):
                                    body_lines.append(f"  {idx+1}. {j['title']} @ {j['company']} (Score: {j.get('score')}) - URL: {j['url']}")
                                    
                                body_str = "\n".join(body_lines)
                                
                                recipient = getattr(config, "RECIPIENT_EMAIL", "your_email@gmail.com")
                                success = gmail.send_email(to=recipient, subject="📊 JS OS Pipeline Report", body=body_str)
                                
                                if success:
                                    send_message("📊 Pipeline report sent to your email!")
                                else:
                                    send_message("Failed to send report email. Check logs.")
                            except Exception as e:
                                send_message(f"Error handling /report: {e}")
                                
                        threading.Thread(target=send_report_worker, daemon=True).start()

                    elif text == "/email":
                        def send_email_worker():
                            try:
                                import config
                                import db
                                from integrations import gmail
                                
                                all_jobs = db.get_all_jobs()
                                target_jobs = [j for j in all_jobs if j.get('status') in ('new', 'applied')]
                                target_jobs.sort(key=lambda x: int(x.get('score') or 0), reverse=True)
                                top_jobs = target_jobs[:10]
                                
                                if not top_jobs:
                                    send_message("No highly scored matches found right now.")
                                else:
                                    recipient = config.RECIPIENT_EMAIL
                                    if not recipient or recipient == "your_email@gmail.com":
                                        send_message("Please configure RECIPIENT_EMAIL in .env first!")
                                    else:
                                        body_lines = ["Job Search OS — Top Matches Today\n"]
                                        for i, j in enumerate(top_jobs, start=1):
                                            body_lines.append(f"{i}. {j['title']} @ {j['company']} — Score: {j.get('score', 0)}\n   {j['url']}\n")
                                            
                                        body_str = "\n".join(body_lines)
                                        subject = "🚀 Job Search OS: Top 10 Matches"
                                        
                                        success = gmail.send_email(to=recipient, subject=subject, body=body_str)
                                        
                                        if success:
                                            send_message("📧 Top jobs sent to your email!")
                                        else:
                                            send_message("Failed to send email. Check logs.")
                            except Exception as e:
                                send_message(f"Error handling /email: {e}")
                                
                        threading.Thread(target=send_email_worker, daemon=True).start()

                    elif text.startswith("/"):
                        send_message("Unknown command. Type /help for options.")
                        
                    else:
                        # Treat free-text as a question for the smart assistant
                        def llm_chat_worker(user_text):
                            import db
                            import traceback
                            import llm
                            
                            try:
                                # Acknowledge receipt natively
                                send_message("*(Thinking...)*")
                                
                                # Append user message to memory immediately
                                db.append_chat_history("user", user_text)
                                
                                # Retrieve recent history (last 10 messages)
                                raw_history = db.get_recent_chat_history(limit=10)
                                
                                system_prompt = "You are the Job Search OS assistant. Answer questions about the job search pipeline briefly. You know about the user's profile: Creative Project Coordinator, 2 years experience, targeting remote PM and AI ops roles."
                                
                                print(f"DEBUG: Processing query using Gemini via {llm.DEFAULT_MODEL}")
                                # Ask the LLM
                                resp = llm.ask(system_prompt, user_text, history=raw_history)
                                
                                # Append bot's response to memory
                                db.append_chat_history("assistant", resp)
                                
                                send_message(resp)
                            except Exception as e:
                                err = f"Error in offline chat processing: {e}\n{traceback.format_exc()}"
                                print(err)
                                send_message("❌ " + err[:200])
                        
                        threading.Thread(target=llm_chat_worker, args=(text,), daemon=True).start()
                
                first_run = False
                        
        except Exception as e:
            # Catch all so listener never dies
            time.sleep(3)
            pass
            
        time.sleep(3)
