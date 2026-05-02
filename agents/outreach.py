"""
Outreach agent: Find company contact info and send manual cold emails.
"""
import sys
import os
import requests
import json
from bs4 import BeautifulSoup

# Allow importing modules from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import llm
import db
import config
from integrations import gmail

def find_hr_email(company_name):
    """
    Finds the company domain using Clearbit and generates candidate HR emails.
    """
    print(f"Searching for domain for company: {company_name}...")
    
    # Overrides for tricky or generic company names
    DOMAIN_OVERRIDES = {
        "tether operations limited": "tether.to",
        "tether": "tether.to",
        "magic": "getmagic.com",
        "infuse": "infusemedia.com",
        "xsolla": "xsolla.com",
        "pavago": "pavago.co",
        "bitfinex": "bitfinex.com",
    }
    
    domain = None
    if company_name.lower() in DOMAIN_OVERRIDES:
        domain = DOMAIN_OVERRIDES[company_name.lower()]
        print(f"Using domain override: {domain}")
    else:
        try:
            url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}"
            response = requests.get(url, timeout=(5, 5))
            response.raise_for_status()
            
            data = response.json()
            if not data:
                print(f"No domain found for {company_name}")
                return []
            
            domain = data[0].get("domain")
            if not domain:
                print(f"No domain field in Clearbit result for {company_name}")
                return []
                
            print(f"Found domain: {domain}")
                
        except Exception as e:
            print(f"Error checking Clearbit for {company_name}: {e}")
            return []

    # Generate patterns
    patterns = [
        f"hr@{domain}",
        f"careers@{domain}",
        f"recruiting@{domain}",
        f"talent@{domain}",
        f"jobs@{domain}"
    ]
    return patterns

def research_company(company_name: str, job_url: str, fallback_description: str = None) -> str:
    """Fetches real company context to personalize cold emails."""
    context = []

    # 1. Fetch the job posting page for tech stack and culture clues
    try:
        print(f"Scraping job URL for context: {job_url}...")
        res = requests.get(job_url, timeout=(5, 5), headers={
            "User-Agent": "Mozilla/5.0"
        })
        soup = BeautifulSoup(res.text, "html.parser")
        # Extract visible text
        text = soup.get_text(separator=" ", strip=True)
        
        # Fallback if scraping returns very little text (e.g., blocked)
        if len(text) < 200 and fallback_description:
            print("Scraping returned minimal text. Falling back to database description.")
            text = fallback_description
            
        context.append(f"Job context: {text[:1500]}")
    except Exception as e:
        print(f"Scraping failed: {e}. Falling back to database description.")
        if fallback_description:
            context.append(f"Job context: {fallback_description[:1500]}")
        else:
            context.append("Job posting: unavailable")

    # 2. Check company's About page via Clearbit
    try:
        clearbit_res = requests.get(
            f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}",
            timeout=(5, 5)
        ).json()
        if clearbit_res:
            company = clearbit_res[0]
            if company.get("description"):
                context.append(f"Company description: {company['description']}")
    except:
        pass

    return "\n".join(context) if context else f"Company: {company_name}"

def generate_cold_email(company_name, job_title, job_url, fallback_description):
    """
    Researches the company and generates a highly personalized cold email.
    """
    company_context = research_company(company_name, job_url, fallback_description)
    
    system_prompt = (
        "You are the candidate writing a cold email to a recruiter. You are an expert at cold outreach emails that actually get replies. "
        "Strictly follow these rules - failure to comply is not an option:\n"
        "- Opening line: Write a highly specific, deep observation about the company's core product, scale, or operational complexity based tightly on the context. Never use generic phrases like 'Your focus aligns with'. Start immediately with the observation. Never make up facts.\n"
        f"- Second sentence: Use ONLY the achievement provided. Never invent percentages, metrics, or results not in the profile.\n"
        f"- Third sentence: After the achievement line, write EXACTLY this sentence: 'More of my AI automation work at https://github.com/navr5135/portfolio'.\n"
        "- Third paragraph: Offer a trial task or quick call in one short line. Example: 'Open to a quick call or trial task.'\n"
        "- Sign off: 'Best, Navaditya'\n"
        "- Total length: under 90 words.\n"
        "- Never use the company name more than once.\n"
        "- NEVER use these phrases: 'dynamic team', 'I am writing to express', 'I look forward to', 'I came across', 'Sincerely', 'I hope'.\n"
        "- Sound like a busy human, not a cover letter. No subject line, just the body."
    )
    
    user_message = f"""
Job Title: {job_title}
Company: {company_name}

Company & Job Context (use this to personalize):
{company_context}

Candidate Profile:
Name: Navaditya
Skills: {", ".join(config.CANDIDATE_PROFILE.get('skills', []))}
AI Skills: {", ".join(config.CANDIDATE_PROFILE.get('ai_skills', []))}
AI Projects: {", ".join(config.CANDIDATE_PROFILE.get('ai_projects', []))}
AI Experience Note: {config.CANDIDATE_PROFILE.get('ai_experience_note', '')}
Experience: 2 years
Achievement: {config.CANDIDATE_PROFILE.get('achievement', '')}
Portfolio: {config.CANDIDATE_PROFILE.get('portfolio', '')}
Location: Chandigarh, India (open to remote)
"""
    
    body = llm.ask(system_prompt, user_message)
    subject = f"Quick question — {job_title} at {company_name}"
    
    return subject, body

def run_outreach(job_id, company_name, job_title, job_url, fallback_description=None, dry_run=False):
    """
    Generates a personalized cold email and either returns it (dry_run) or sends it.
    """
    candidates = find_hr_email(company_name)
    if not candidates:
        print(f"Could not find any contact emails for {company_name}.")
        return None
    
    to_email = candidates[0]
    # Use careers@ as CC if available, otherwise no CC
    cc_email = candidates[1] if len(candidates) > 1 else None
    
    subject, body = generate_cold_email(company_name, job_title, job_url, fallback_description)
    
    if not body:
        print("Failed to generate cold email body.")
        return None

    # Safety catch for generic emails
    generic_prefixes = ["hr@", "careers@", "jobs@", "recruiting@", "hello@", "info@", "talent@"]
    if not dry_run and any(to_email.lower().startswith(p) for p in generic_prefixes):
        print("⚠ Unverified email pattern — recommend manual verification before sending.")
        print("Forcing dry_run=True to prevent blind bounces.")
        dry_run = True

    if dry_run:
        return {
            "to": to_email,
            "cc": cc_email,
            "subject": subject,
            "body": body
        }
    
    # Actually send
    print(f"Sending outreach to {to_email} (CC: {cc_email})...")
    success = gmail.send_email(to_email, subject, body, cc=cc_email)
    
    if success:
        notes = f"Cold outreach sent to {to_email} (CC: {cc_email})"
        db.update_status(job_id, 'outreached', notes=notes)
        print("Outreach successful and database updated.")
    else:
        print("Outreach failed.")
        
    return success

if __name__ == "__main__":
    # Quick test
    test_companies = ["Stripe"]
    for company in test_companies:
        print(f"\nTesting {company}:")
        print(find_hr_email(company))
