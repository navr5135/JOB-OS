import db
from integrations import gmail

def main():
    print("Fetching applied jobs from database...")
    jobs = db.get_jobs_by_status('applied')
    
    # Exact Output Mapping from the LLM based on user's confirmation
    payloads = {
        "Xsolla": {
            "to": "hr@xsolla.com",
            "cc": "careers@xsolla.com",
            "subject": "Quick question — Operations Project Manager at Xsolla",
            "body": "Xsolla's global game distribution platform handles complex workflows for 1,500+ developers, requiring seamless cross-functional coordination. Oversaw creative operations at a US digital marketing agency, coordinating designers, UI/UX, and video teams, conducting final QA on all deliverables, managing client relationships, and handling billing across simultaneous accounts. More of my AI automation work at https://github.com/navr5135/portfolio. Open to a quick call or trial task.\n\nBest, Navaditya"
        },
        "INFUSE": {
            "to": "hr@infusemedia.com",
            "cc": "careers@infusemedia.com",
            "subject": "Quick question — Middle Project Manager Internal Systems and Processes at INFUSE",
            "body": "INFUSE's internal systems require meticulous coordination across cross-functional teams to maintain compliance with data privacy regulations. Oversaw creative operations at a US digital marketing agency — coordinating designers, UI/UX, and video teams, conducting final QA on all deliverables, managing client relationships, and handling billing across simultaneous accounts. More of my AI automation work at https://github.com/navr5135/portfolio. Open to a quick call or trial task.\n\nBest, Navaditya"
        },
        "Bitfinex": {
            "to": "hr@bitfinex.com",
            "cc": "careers@bitfinex.com",
            "subject": "Quick question — HR People Operations Specialist (Fully Remote, Worldwide) at Bitfinex",
            "body": "Your global impact from a small core team highlights a unique balance of agility and scalability. Oversaw creative operations at a US digital marketing agency — coordinating designers, UI/UX, and video teams, conducting final QA on all deliverables, managing client relationships, and handling billing across simultaneous accounts. More of my AI automation work at https://github.com/navr5135/portfolio. Open to a quick call or trial task.\n\nBest, Navaditya"
        },
        "Pavago": {
            "to": "hr@pavago.co",
            "cc": "careers@pavago.co",
            "subject": "Quick question — Marketing Coordinator at Pavago",
            "body": "Pavago’s scale demands meticulous coordination across diverse projects and stakeholders. Oversaw creative operations at a US digital marketing agency — coordinating designers, UI/UX, and video teams, conducting final QA on all deliverables, managing client relationships, and handling billing across simultaneous accounts. More of my AI automation work at https://github.com/navr5135/portfolio. Open to a quick call or trial task.\n\nBest, Navaditya"
        }
    }
    
    for job in jobs:
        c_lower = job['company'].lower()
        
        for p_key, payload in payloads.items():
            if p_key.lower() in c_lower:
                # Basic filter to ensure we execute on the right job role
                if "junior" in job['title'].lower() or "senior frontend" in job['title'].lower():
                    continue
                    
                print("="*80)
                print(f"!!! SENDING LIVE OUTREACH FOR: {job['title']} @ {job['company']} !!!")
                print(f"URL: {job['url']}")
                print("="*80)
                
                success = gmail.send_email(
                    payload['to'], 
                    payload['subject'], 
                    payload['body'], 
                    cc=payload['cc']
                )
                
                if success:
                    db.update_status(job['id'], 'outreached', notes=f"Cold outreach sent to {payload['to']} natively from verified local output.")
                    print("Outreach database status updated successfully.\n")
                else:
                    print("Failed to send outreach natively.\n")

if __name__ == "__main__":
    main()
