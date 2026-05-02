"""
Application agent: Tailor CV and cover letter for specific job listings.
"""
import os
import sys
import re

# Allow importing modules from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import llm
import db
import config

OUTPUT_DIR = "output"

def sanitize_filename(name):
    """Sanitizes strings to be used as filenames by replacing special characters with underscores."""
    # Replace anything that isn't alphanumeric, space, or hyphen with an underscore
    sanitized = re.sub(r'[^a-zA-Z0-9\s\-]', '_', name)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    # Replace multiple underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip('_')

def run_application():
    """Main loop for tailoring CVs and cover letters for new jobs."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    new_jobs = db.get_jobs_by_status("new")
    if not new_jobs:
        print("No 'new' jobs found in the database.")
        return

    print(f"Found {len(new_jobs)} new jobs. Generating applications...")

    for job in new_jobs:
        job_id = job.get('id')
        title = job.get('title')
        company = job.get('company')
        description = job.get('description', '')[:1500]

        print(f"Processing application for {title} at {company}...")

        # 1. CV Tailoring
        cv_system = (
            "You are an expert CV writer. Return 3 bullet points tailored to "
            "this specific job. Each bullet should start with a strong action verb and "
            "include a measurable result. Be concise."
        )
        cv_user = f"Job: {title} at {company}\nDescription: {description}\nCandidate: {config.CANDIDATE_PROFILE}"
        cv_bullets = llm.ask_fast(cv_system, cv_user)

        # 2. Cover Letter
        cl_system = (
            "You are an expert cover letter writer. Write a 150-word cover "
            "letter. Be specific to the company and role. Professional but human tone."
        )
        cl_user = cv_user  # Same context as CV
        cover_letter = llm.ask_fast(cl_system, cl_user)

        if not cv_bullets.strip() or not cover_letter.strip():
            print(f"LLM returned empty content for {title} at {company}. Leaving job as 'new'.")
            db.update_status(job_id, 'new', notes="Application generation failed: empty LLM output.")
            continue

        # Truncate cover letter to max 200 words
        words = cover_letter.split()
        if len(words) > 200:
            print(f"Warning: Cover letter for {company} was truncated from {len(words)} to 200 words.")
            cover_letter = ' '.join(words[:200])

        # 3. Save to file
        filename = sanitize_filename(f"{company}_{title}") + ".txt"
        file_path = os.path.join(OUTPUT_DIR, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"JOB: {title} at {company}\n")
            f.write("="*40 + "\n\n")
            f.write("TAILORED CV BULLETS:\n")
            f.write(cv_bullets + "\n\n")
            f.write("="*40 + "\n\n")
            f.write("COVER LETTER:\n")
            f.write(cover_letter + "\n")

        # 4. Update Database
        db.update_status(job_id, 'applied', notes="Generated CV and Cover Letter.")
        print(f"Successfully generated application and saved to {file_path}")

if __name__ == "__main__":
    run_application()
