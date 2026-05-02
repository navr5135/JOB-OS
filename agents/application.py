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

    new_jobs.sort(key=lambda x: int(x.get('score') or 0), reverse=True)
    eligible_jobs = [
        job for job in new_jobs
        if int(job.get('score') or 0) >= config.MIN_APPLICATION_SCORE
    ]
    target_jobs = eligible_jobs[:config.MAX_APPLICATIONS_PER_RUN]

    print(
        f"Found {len(new_jobs)} new jobs. "
        f"Generating up to {len(target_jobs)} applications "
        f"(score >= {config.MIN_APPLICATION_SCORE})."
    )

    if not target_jobs:
        print("No jobs met the application score threshold.")
        return

    generated_count = 0
    for job in target_jobs:
        if not llm.can_call():
            print("LLM budget unavailable. Stopping application generation.")
            break

        job_id = job.get('id')
        title = job.get('title')
        company = job.get('company')
        description = job.get('description', '')[:1500]

        print(f"Processing application for {title} at {company}...")

        system_prompt = (
            "You are an expert job application writer. Return ONLY valid JSON "
            "with keys: cv_bullets (array of exactly 3 concise tailored bullets) "
            "and cover_letter (string, 120-170 words). Be specific to the role, "
            "professional, and human. Do not invent facts."
        )
        user_message = (
            f"Job: {title} at {company}\n"
            f"Description: {description}\n"
            f"Candidate: {config.CANDIDATE_PROFILE}"
        )
        draft = llm.ask_json(system_prompt, user_message, model=llm.FAST_MODEL)
        cv_items = draft.get("cv_bullets", []) if isinstance(draft, dict) else []
        cover_letter = draft.get("cover_letter", "") if isinstance(draft, dict) else ""
        if isinstance(cv_items, str):
            cv_bullets = cv_items
        else:
            cv_bullets = "\n".join(f"- {item}" for item in cv_items if str(item).strip())

        if not cv_bullets.strip() or not cover_letter.strip():
            print(f"LLM returned empty content for {title} at {company}. Leaving job as 'new'.")
            db.update_status(job_id, 'new', notes="Application generation failed: empty LLM output.")
            if llm.is_rate_limited():
                print("Stopping application generation because Gemini rate limit was reached.")
                break
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
        generated_count += 1
        print(f"Successfully generated application and saved to {file_path}")

    print(f"Application generation complete: {generated_count} generated.")

if __name__ == "__main__":
    run_application()
