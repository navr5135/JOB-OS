import db
from agents import outreach
import config
from integrations import gmail

def main():
    # 1. SEND LIVE EMAIL FOR TETHER
    # Find the job in DB
    jobs = db.get_jobs_by_status('applied')
    tether_job = next((j for j in jobs if "AI Product Manager" in j['title'] and "Tether" in j['company']), None)
    
    if tether_job:
        print("!!! SENDING LIVE TETHER EMAIL !!!")
        to_email = "hr@tether.to"
        cc_email = "careers@tether.to"
        subject = "Quick question — AI Product Manager at Tether Operations Limited"
        body = """Tether's work on AI-native payment infrastructure across 150+ countries is exactly the kind of operational complexity I want to work on.

Oversaw creative operations at a US digital marketing agency — coordinating designers, UI/UX, and video teams, conducting final QA on all deliverables, managing client relationships and billing across simultaneous accounts. More of my AI automation work at github.com/navr5135/portfolio.

Open to a quick call or trial task.

Best,
Navaditya"""
        
        success = gmail.send_email(to_email, subject, body, cc=cc_email)
        if success:
            db.update_status(tether_job['id'], 'outreached', notes=f"Cold outreach sent to {to_email} (CC: {cc_email}) with custom copy")
            print("Successfully sent Tether email live.\n")
        else:
            print("Failed to send Tether email live.\n")
    else:
        print("Tether job not found in applied queue.\n")


    # 2. SEQUENCE DRY RUN FOR TARGETS
    targets = {
        "Xsolla": "Operations Project Manager",
        "Pavago": "Marketing Coordinator",
        "Bitfinex": "HR People Operations",
        "INFUSE": "Middle Project Manager"
    }
    
    for job in jobs:
        c_name = job['company']
        t_name = job['title']
        
        # Check if company matches and title has the key substring
        for target_co, target_title in targets.items():
            if target_co.lower() in c_name.lower() and target_title.lower() in t_name.lower():
                print("="*80)
                print(f"Executing Dry Run Outreach for: {t_name} @ {c_name}")
                print(f"URL: {job['url']}")
                print("="*80)
                
                # Use a dummy URL so research_company fails scraping fast and falls back to description!
                # This ensures Qwen doesn't choke on huge HTML contexts and generates instantly.
                fast_run_url = "https://himalayas.app/404-bypass-url"
                
                result = outreach.run_outreach(
                    job['id'],
                    c_name,
                    t_name,
                    fast_run_url,
                    fallback_description=job.get('description', ''),
                    dry_run=True
                )
                
                if result:
                    print(f"TO: {result['to']}")
                    print(f"CC: {result.get('cc')}")
                    print(f"SUBJECT: {result['subject']}")
                    print("-" * 20)
                    print(result['body'])
                    print("="*80 + "\n")
                else:
                    print("Failed to generate outreach.\n")

if __name__ == "__main__":
    main()
