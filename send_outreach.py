import db
from agents import outreach

def main():
    print("Fetching jobs from database...")
    jobs = db.get_jobs_by_status('applied')
    
    # Priority targets specified by the user
    priority_companies = ["Magic", "Tether Operations Limited", "Tether"]
    
    targets = [j for j in jobs if any(c.lower() in j['company'].lower() for c in priority_companies)]
    
    if not targets:
        print("No priority targets found in applied queue.")
        return
        
    for job in targets:
        print("="*60)
        print(f"Executing Dry Run Outreach for: {job['title']} @ {job['company']}")
        print(f"URL: {job['url']}")
        print("="*60)
        
        # Run outreach in dry-run mode
        result = outreach.run_outreach(
            job['id'],
            job['company'],
            job['title'],
            job['url'],
            fallback_description=job.get('description'),
            dry_run=True
        )
        
        if result:
            print(f"TO: {result['to']}")
            print(f"CC: {result['cc']}")
            print(f"SUBJECT: {result['subject']}")
            print("-" * 20)
            print(result['body'])
            print("="*60 + "\n")
        else:
            print("Failed to generate outreach.")

if __name__ == "__main__":
    main()
