"""
Discovery agent: Scrape and score job listings from various sources.
"""
import requests
import sys
import os
from bs4 import BeautifulSoup
import json

# Allow importing modules from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import llm
import db
from config import CANDIDATE_PROFILE
from integrations import notion

# Source config
REMOTIVE_TARGETS = [
    "https://remotive.com/api/remote-jobs?category=business&limit=20&search=coordinator",
    "https://remotive.com/api/remote-jobs?category=business&limit=20&search=associate",
    "https://remotive.com/api/remote-jobs?category=marketing&limit=20&search=coordinator"
]

WWR_TARGETS = [
    "https://weworkremotely.com/categories/remote-management-jobs.rss",
    "https://weworkremotely.com/categories/remote-business-jobs.rss"
]

HIMALAYAS_TARGETS = [
    "https://himalayas.app/jobs/api?limit=20&jobTypes=full-time&q=project+coordinator&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&jobTypes=full-time&q=creative+operations&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&jobTypes=full-time&q=project+manager&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&q=ai+operations&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&q=automation+specialist&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&q=ai+project+manager&worldwide=true",
    "https://himalayas.app/jobs/api/search?q=project+coordinator&worldwide=true&limit=20",
    "https://himalayas.app/jobs/api/search?q=business+analyst&worldwide=true&limit=20",
    "https://himalayas.app/jobs/api/search?q=ai+operations&worldwide=true&limit=20",
    "https://himalayas.app/jobs/api?limit=20&q=operations+associate&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&q=junior+project+manager&worldwide=true",
    "https://himalayas.app/jobs/api?limit=20&q=coordinator+remote&worldwide=true"
]

JOBICY_TARGETS = [
    "https://jobicy.com/api/v2/remote-jobs?count=20&industry=management",
    "https://jobicy.com/api/v2/remote-jobs?count=20&tag=coordinator"
]

FDW_RSS = "https://4dayweek.io/remote-jobs/feed"

REMOTEOK_API = "https://remoteok.com/api?tag=manager&limit=20"

def fetch_remotive():
    """Fetches job listings from Remotive API."""
    jobs = []
    for url in REMOTIVE_TARGETS:
        print(f"Fetching from Remotive: {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get('jobs', [])
            for job in data:
                jobs.append({
                    "title": job.get("title"),
                    "company_name": job.get("company_name"),
                    "url": job.get("url"),
                    "description": job.get("description"),
                    "source": "Remotive"
                })
        except Exception as e:
            print(f"Error fetching from Remotive: {e}")
    return jobs

def fetch_wwr():
    """Fetches job listings from We Work Remotely RSS feeds."""
    jobs = []
    for url in WWR_TARGETS:
        print(f"Fetching from We Work Remotely: {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")[:15] # Limit per category
            
            for item in items:
                raw_title = item.find("title").text if item.find("title") else "Unknown"
                # WWR Title format: "Company: Job Title"
                if ": " in raw_title:
                    company, title = raw_title.split(": ", 1)
                else:
                    company, title = "Unknown", raw_title
                
                jobs.append({
                    "title": title,
                    "company_name": company,
                    "url": item.find("link").text if item.find("link") else None,
                    "description": item.find("description").text if item.find("description") else "",
                    "source": "WWR"
                })
        except Exception as e:
            print(f"Error fetching from WWR ({url}): {e}")
    return jobs

def fetch_himalayas():
    """Fetches job listings from Himalayas API for multiple queries."""
    jobs = []
    for url in HIMALAYAS_TARGETS:
        print(f"Fetching from Himalayas: {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get('jobs', [])
            for job in data:
                jobs.append({
                    "title": job.get("title"),
                    "company_name": job.get("companyName"),
                    "url": job.get("guid"), # Using guid as the permanent URL
                    "description": job.get("description", job.get("excerpt", "")),
                    "source": "Himalayas"
                })
        except Exception as e:
            print(f"Error fetching from Himalayas ({url}): {e}")
    return jobs

def fetch_remoteok():
    """Fetches job listings from RemoteOK API."""
    jobs = []
    print(f"Fetching from RemoteOK: {REMOTEOK_API}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(REMOTEOK_API, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # RemoteOK returns a legal disclaimer as the first element
        if len(data) > 1:
            for job in data[1:]:
                jobs.append({
                    "title": job.get("position"),
                    "company_name": job.get("company"),
                    "url": job.get("url"),
                    "description": job.get("description"),
                    "source": "RemoteOK"
                })
    except Exception as e:
        print(f"Error fetching from RemoteOK: {e}")
    return jobs

def fetch_jobicy():
    """Fetches job listings from Jobicy API."""
    jobs = []
    for url in JOBICY_TARGETS:
        print(f"Fetching from Jobicy: {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get('jobs', [])
            for job in data:
                jobs.append({
                    "title": job.get("jobTitle"),
                    "company_name": job.get("companyName"),
                    "url": job.get("url"),
                    "description": job.get("jobExcerpt", ""),
                    "source": "Jobicy"
                })
        except Exception as e:
            print(f"Error fetching from Jobicy ({url}): {e}")
    return jobs

def fetch_4dayweek():
    """Fetches job listings from 4dayweek.io RSS feed."""
    jobs = []
    print(f"Fetching from 4dayweek: {FDW_RSS}...")
    try:
        response = requests.get(FDW_RSS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")[:20]
        
        for item in items:
            jobs.append({
                "title": item.find("title").text if item.find("title") else "Unknown",
                "company_name": "4dayweek", # Actual company is usually in title or desc, hard to parse cleanly without HTML check, fallback to source name or attempt split
                "url": item.find("link").text if item.find("link") else None,
                "description": item.find("description").text if item.find("description") else "",
                "source": "4dayweek.io"
            })
    except Exception as e:
        print(f"Error fetching from 4dayweek: {e}")
    return jobs

def pre_filter(job):
    """
    Pre-filters jobs by title to save ML tokens and compute.
    Returns:
    - 'reject': discard job outright
    - 'accept': skip LLM, auto-score 75
    - 'process': proceed to LLM normally
    """
    title = job.get('title', '').lower()
    
    reject_keywords = ["engineer", "developer", "devops", "designer", "scientist",
                       "therapist", "clinical", "medical", "sales", "sdr", "nurse",
                       "accountant", "legal", "driver", "chef",
                       "avp", "vice president", "director", "c-suite", "chief",
                       "partner", "principal", "staff ", "programmer", 
                       ".net", "c#", "java", "ruby", "php", "swift", 
                       "kotlin", "flutter", "android", "ios"]
                       
    accept_keywords = ["coordinator", "operations associate", "project associate"]
    
    for kw in reject_keywords:
        if kw in title:
            return 'reject'
            
    for kw in accept_keywords:
        if kw in title:
            return 'accept'
            
    return 'process'

def analyze_job(job):
    """Uses LLM to analyze the job fit for the candidate."""
    system_prompt = (
        "You are a job fit analyser. Given a job description and candidate profile, "
        "return ONLY a JSON object with keys: "
        "score (0-100 integer), "
        "reason (one sentence string), "
        "apply (boolean), "
        "india_friendly (boolean), "
        "seniority_level (string: 'entry', 'mid', 'senior', 'executive'). "
        "Guidelines for score (Candidate has 3 Tracks: Project/Creative Operations, Business Analytics, AI Automation & Integration):\n"
        "Strong Match (80-100):\n"
        "- AI Project Manager / AI Program Coordinator\n"
        "- AI Operations Specialist / AI Tools Specialist\n"
        "- Automation Specialist / Workflow Automation Manager\n"
        "- AI Integration Specialist / No-code AI Developer\n"
        "- Digital Transformation Coordinator\n"
        "- Prompt Engineer (workflow/coordination focused, non-technical)\n"
        "- Creative/Design Project Management & Operations\n"
        "Moderate Match (60-80):\n"
        "- Account Management / Client Success\n"
        "- Talent Acquisition / HR Coordinator\n"
        "- Business Business Operations / Business Analytics\n"
        "- Content / Social Media Management\n"
        "Reject (0-20):\n"
        "- ML Engineer / AI Research Scientist (too technical)\n"
        "- Data Scientist (requires heavy math/statistics degree)\n"
        "- Software Engineer / DevOps (coding-only roles)\n"
        "Seniority Scoring Rules:\n"
        "- Reduce score by 30 points if title contains: 'Senior Manager', 'Director', 'Head of', 'VP', 'Chief', 'Lead' (with Manager), 'Principal'.\n"
        "- Keep score as-is if title contains: 'Coordinator', 'Associate', 'Junior', 'Assistant', 'Specialist', 'Analyst', 'Executive' (in non-US context).\n"
        "- If title contains 'Manager' and company appears to be a startup (description has 'startup', 'early stage', 'small team', 'seed', 'Series A', 'growing team'): Keep original score, set seniority_level to 'mid'.\n"
        "- If title contains 'Manager' and company appears established/large: Reduce score by 25 points, set seniority_level to 'senior'.\n"
        "Guidelines for india_friendly: "
        "Set to true if: 'worldwide', 'global', 'anywhere', 'all timezones', 'India', 'Asia', 'IST', 'UTC+5', "
        "or if it mentions 'contractor'/'contract'. "
        "Set to false if: 'US only', 'UK only', 'EU only', 'must be located in', specific US states (e.g., 'California residents')."
    )
    
    user_message = f"""
    CANDIDATE PROFILE:
    {json.dumps(CANDIDATE_PROFILE, indent=2)}
    
    JOB LISTING (Source: {job.get('source')}):
    Title: {job.get('title')}
    Company: {job.get('company_name')}
    Description: {job.get('description', '')[:2000]}... [truncated]
    """
    
    return llm.ask_json(system_prompt, user_message, model=llm.FAST_MODEL)

def run_discovery():
    """Orchestrates job discovery from all sources."""
    print("Starting Multi-Source Discovery...")
    
    all_raw_jobs = []
    all_raw_jobs.extend(fetch_remotive())
    all_raw_jobs.extend(fetch_wwr())
    all_raw_jobs.extend(fetch_himalayas())
    all_raw_jobs.extend(fetch_remoteok())
    all_raw_jobs.extend(fetch_jobicy())
    all_raw_jobs.extend(fetch_4dayweek())
    
    if not all_raw_jobs:
        print("No jobs found from any source.")
        return

    # Deduplicate by URL within this run
    seen_urls_batch = set()
    unique_jobs = []
    for job in all_raw_jobs:
        url = job.get('url')
        if url and url not in seen_urls_batch:
            seen_urls_batch.add(url)
            unique_jobs.append(job)
            
    print(f"\nTotal jobs discovered: {len(all_raw_jobs)}")
    print(f"Unique jobs after deduplication: {len(unique_jobs)}")
    
    seen_urls_db = db.get_seen_urls()
    new_jobs = []
    
    for job in unique_jobs:
        if job.get('url') in seen_urls_db:
            db.update_last_seen(job.get('url'))
        else:
            new_jobs.append(job)
            
    print(f"Skipping {len(unique_jobs) - len(new_jobs)} already-seen jobs. Analyzing {len(new_jobs)} new jobs.")
    
    results = []
    processed_count = 0
    saved_count = 0
    skipped_india_count = 0
    skipped_score_count = 0
    skipped_seniority_count = 0
    
    pre_rejected_count = 0
    auto_accepted_count = 0
    sent_to_llm_count = 0
    
    for job in new_jobs:
        processed_count += 1
        title = job.get('title', '')
        company = job.get('company_name', '')
        source = job.get('source', '')
        
        try:
            print(f"[{processed_count}/{len(new_jobs)}] Pre-filtering {title} at {company} ({source})...")
        except UnicodeEncodeError:
            print(f"[{processed_count}/{len(new_jobs)}] Pre-filtering [Unicode Title] at [Unicode Company] ({source})...")
            
        filter_status = pre_filter(job)
        
        if filter_status == 'reject':
            print(" -> REJECTED by pre-filter.")
            pre_rejected_count += 1
            continue
            
        if filter_status == 'accept':
            print(" -> ACCEPTED by pre-filter (Auto 75).")
            auto_accepted_count += 1
            analysis = {
                'score': 75,
                'reason': 'Auto-accepted based on highly relevant title.',
                'apply': True,
                'india_friendly': True, # Assume true for auto-accepts, or we'd need LLM to verify. Assuming mostly Remote worldwide.
                'seniority_level': 'mid'
            }
        else:
            print(" -> Sent to LLM.")
            sent_to_llm_count += 1
            analysis = analyze_job(job)
            
        score = analysis.get('score', 0)
        reason = analysis.get('reason', 'No reason provided.')
        apply = analysis.get('apply', False)
        india_friendly = analysis.get('india_friendly', False)
        seniority_level = analysis.get('seniority_level', 'unknown')
        
        # Filtering logic: Only save if mid/entry AND high score AND india friendly
        if seniority_level in ['entry', 'mid'] and score >= 60 and india_friendly:
            db.insert_job(
                title=job.get('title'),
                company=job.get('company_name'),
                url=job.get('url'),
                description=job.get('description'),
                score=score,
                status='new',
                notes=f"[{seniority_level.upper()}] {reason}"
            )
            saved_count += 1
        elif seniority_level not in ['entry', 'mid']:
            skipped_seniority_count += 1
        elif score < 60:
            skipped_score_count += 1
        else:
            skipped_india_count += 1
        
        results.append({
            "source": job.get('source'),
            "company": job.get('company_name'),
            "title": job.get('title'),
            "score": score,
            "seniority": seniority_level,
            "india_ok": "Yes" if india_friendly else "No"
        })

    # Summary Table
    print("\n" + "="*120)
    print(f"{'SOURCE':<10} | {'COMPANY':<20} | {'TITLE':<35} | {'SCORE':<5} | {'SENIORITY':<10} | {'INDIA OK':<8}")
    print("-" * 120)
    for res in results:
        try:
            source = res['source'][:9]
            company = str(res['company'])[:19]
            title = str(res['title'])[:34]
            seniority = str(res['seniority'])[:9]
            print(f"{source:<10} | {company:<20} | {title:<35} | {res['score']:<5} | {seniority:<10} | {res['india_ok']:<8}")
        except:
            print(f"{'[Err]':<10} | {'[Err]':<20} | {'[Err]':<35} | {res['score']:<5} | {'[Err]':<10} | {res['india_ok']:<8}")
    print("="*120)
    
    # Source Breakdown
    print("\nSource Breakdown (Unique Jobs Searched):")
    source_counts = {}
    for job in unique_jobs:
        src = job.get('source', 'Unknown')
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in source_counts.items():
        print(f"- {src}: {count}")
    
    print(f"\nProcessing Stats: {pre_rejected_count} pre-rejected | {auto_accepted_count} auto-accepted | {sent_to_llm_count} sent to LLM")
    print(f"Summary: {saved_count} jobs saved ({skipped_seniority_count} skipped - too senior, {skipped_india_count} skipped - not India friendly, {skipped_score_count} skipped - low score)")
    
    # Immediately sync newly discovered jobs to Notion
    if saved_count > 0:
        notion.sync_all_jobs()

if __name__ == "__main__":
    run_discovery()
