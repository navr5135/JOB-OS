import json
import db
import llm
import config
from integrations import gmail

SYSTEM_PROMPT = f"""You are Navaditya's Job Search OS Agent, an autonomous AI assistant powered by local infrastructure. 
Navaditya is a {config.CANDIDATE_PROFILE['role']} looking for roles: {', '.join(config.CANDIDATE_PROFILE['target_roles'])}.

You are the central intelligence of a larger system. Your backend automatically scrapes job boards (Himalayas, We Work Remotely, Remotive, etc.) daily. 

You have access to the following tools:
1. "SEARCH_MEMORY" - Searches long-term memory for semantic facts. Input: search query.
2. "SAVE_MEMORY" - Saves a fact to long-term memory. Input: fact to save.
3. "READ_GMAIL" - Retrieves the 5 most recent unread emails. Input: search query (e.g., "from:xsolla", "is:unread").
4. "GET_DB_STATS" - Gets current job application pipeline metrics. Input: "".
5. "SYNC_NOTION" - Forces an immediate sync of the local job pipeline to Notion. Input: "".
6. "GET_TOP_JOBS" - Retrieves the top 5 highest-scored new jobs from the database. Input: "".
7. "SEND_EMAIL" - Sends an email natively. Input format MUST be EXACTLY: "email_address|subject|body".
8. "RUN_DISCOVERY" - Manually triggers the backend web scrapers to gather fresh jobs from Himalayas, Remotive, and WWR right now. Input: "".
9. "FINAL_ANSWER" - When you have the final response for the user. Input: your response.

You MUST respond ONLY with valid JSON using this format:
{{
  "thought": "your reasoning here",
  "action": "TOOL_NAME",
  "action_input": "input for the tool"
}}

Execute tools one by one. Once you gather enough context, use FINAL_ANSWER.
"""

def run_query(user_text, raw_history):
    """Executes the ReAct loop until a FINAL_ANSWER is reached or it hits max_steps."""
    # Convert SQLite history objects to strict Ollama dicts
    messages = []
    if raw_history:
        for msg in raw_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
    # Inject current query
    current_prompt = f"User Query: {user_text}\n\nStrict JSON response required:"
    
    max_steps = 4
    step = 0
    
    while step < max_steps:
        # We use the smarter 8b model for ReAct parsing
        response_text = llm.ask(SYSTEM_PROMPT, current_prompt, json_format=True, history=messages)
        
        try:
            parsed = json.loads(response_text)
            action = parsed.get("action")
            action_input = parsed.get("action_input", "")
            thought = parsed.get("thought", "")
            
            print(f"ReAct Thought: {thought}")
            print(f"ReAct Action: {action}('{action_input}')")
            
            if action == "FINAL_ANSWER":
                return action_input
                
            elif action == "SEARCH_MEMORY":
                results = llm.semantic_search(action_input, top_k=2)
                context = "\n".join([f"- {r['content']} (similarity: {r['similarity']:.2f})" for r in results]) if results else "No memory found."
                observation = f"Observation: {context}"
                
            elif action == "SAVE_MEMORY":
                # We need an embedding for the fact
                emb = llm.get_embedding(action_input)
                if emb:
                    db.insert_vector_memory("General Chat Fact", action_input, emb)
                    observation = "Observation: Memory successfully saved."
                else:
                    observation = "Observation: Failed to generate embedding vector."
                    
            elif action == "READ_GMAIL":
                results = gmail.get_recent_emails(query=action_input, limit=5)
                observation = f"Observation: \n" + "\n".join(results)
                
            elif action == "GET_DB_STATS":
                stats = db.get_database_stats()
                observation = f"Observation: Current Pipeline Data = {stats}"

            elif action == "SYNC_NOTION":
                from integrations import notion
                notion.sync_all_jobs()
                observation = f"Observation: Notion synchronization completed successfully."
                
            elif action == "GET_TOP_JOBS":
                jobs = db.get_jobs_by_status("new")
                jobs.sort(key=lambda x: float(x.get('score', 0) or 0), reverse=True)
                top_jobs = jobs[:5]
                if not top_jobs:
                    observation = "Observation: No new jobs available in the DB."
                else:
                    lines = [f"- {j['title']} at {j['company']} (Score: {j.get('score')}) | URL: {j.get('url')}" for j in top_jobs]
                    observation = "Observation: Top 5 New Jobs:\n" + "\n".join(lines)
                    
            elif action == "SEND_EMAIL":
                try:
                    # Expecting format "email|subject|body"
                    parts = action_input.split('|', 2)
                    if len(parts) == 3:
                        to_email, subject, body = parts
                        success = gmail.send_email(to_email.strip(), subject.strip(), body.strip())
                        observation = f"Observation: Email {'sent successfully' if success else 'failed to send'}."
                    else:
                        observation = "Observation: Invalid parameter format. Must be 'email|subject|body'."
                except Exception as e:
                    observation = f"Observation: Extraction Error: {e}"

            elif action == "RUN_DISCOVERY":
                from agents import discovery
                try:
                    discovery.run_discovery()
                    observation = "Observation: Successfully ran background scrapers and gathered fresh job data into the database."
                except Exception as e:
                    observation = f"Observation: Error running discovery scrapers: {e}"

            else:
                observation = f"Observation: Valid action not found. Action '{action}' is invalid."
            
            # Inject observation back into prompt for the next loop
            current_prompt += f"\n{response_text}\n\n{observation}\n\nNow provide your next strict JSON instruction:"
            
        except json.JSONDecodeError:
            print("ReAct JSON Error: Failed to parse LLM output.")
            # Penalize and ask again
            current_prompt += f"\nSystem Error: You returned invalid JSON. Try again using EXACTLY the tool JSON schema."
            
        step += 1
        
    return "I am taking too long to think via my local processing node. Please ask your question in another way."
