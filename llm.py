"""
Gemini API wrapper for all AI calls. This module interacts with the new Google GenAI SDK.
"""
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REQUEST_BUDGET = int(os.getenv("GEMINI_DAILY_REQUEST_BUDGET", "18"))
REQUESTS_USED = 0
RATE_LIMITED = False

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in .env. API calls will fail.")

# Initialize the client globally
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", DEFAULT_MODEL)

def calls_remaining():
    return max(REQUEST_BUDGET - REQUESTS_USED, 0)

def can_call():
    return bool(client and not RATE_LIMITED and calls_remaining() > 0)

def is_rate_limited():
    return RATE_LIMITED

def ask(system_prompt, user_message, json_format=False, disable_thinking=True, model=DEFAULT_MODEL, history=None):
    """
    Sends a chat request to the Gemini API using the new google-genai SDK.
    """
    global REQUESTS_USED, RATE_LIMITED
    if not client:
        return ""
    if RATE_LIMITED:
        print("Gemini rate limit already reached. Skipping LLM call.")
        return ""
    if REQUESTS_USED >= REQUEST_BUDGET:
        print(f"Gemini request budget reached ({REQUESTS_USED}/{REQUEST_BUDGET}). Skipping LLM call.")
        return ""
        
    try:
        kwargs = {}
        if json_format:
            kwargs["response_mime_type"] = "application/json"
            
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            **kwargs
        )
        
        contents = []
        if history:
            for msg in history:
                role = msg.get("role", "user")
                if role in ["assistant", "system", "model"]:
                    role = "model"
                else:
                    role = "user"
                
                contents.append(
                    types.Content(
                        role=role, 
                        parts=[types.Part.from_text(text=msg.get("content", ""))]
                    )
                )
                
        contents.append(user_message)
        
        REQUESTS_USED += 1
        print(f"Gemini request {REQUESTS_USED}/{REQUEST_BUDGET} using {model}.")
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
        
        return response.text
        
    except Exception as e:
        error_text = str(e)
        if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
            RATE_LIMITED = True
            print(f"Gemini rate limit reached for {model}. Stopping further LLM calls this run.")
            return ""
        print(f"Error calling Gemini API ({model}): {e}")
        return ""

def ask_fast(system_prompt, user_message, history=None):
    """Uses the FAST_MODEL for quicker responses on simpler tasks."""
    return ask(system_prompt, user_message, model=FAST_MODEL, history=history)

def ask_json(system_prompt, user_message, model=DEFAULT_MODEL):
    """
    Calls ask() and parses the result as JSON, retrying once if parsing fails.
    """
    content = ask(system_prompt, user_message, json_format=True, model=model)
    
    try:
        if not content:
            raise ValueError("Empty response")
        return json.loads(content)
    except (json.JSONDecodeError, TypeError, ValueError):
        if RATE_LIMITED or calls_remaining() <= 0:
            print("Failed to parse JSON and no LLM budget remains.")
            return {}
        print("Failed to parse JSON, retrying...")
        content = ask(system_prompt, user_message + " (Return ONLY valid JSON without markdown block wrappers)", json_format=True, model=model)
        try:
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except (json.JSONDecodeError, TypeError, ValueError):
            print("Failed to parse JSON on retry.")
            return {}

# --- VECTOR RAG MEMORY ---

import numpy as np

EMBED_MODEL = "text-embedding-004"

def get_embedding(text):
    """Generates a mathematical embedding vector from Gemini for the given text."""
    if not client:
        return []
    try:
        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
        )
        # Handle new SDK response schema: response.embeddings[0].values
        return response.embeddings[0].values
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

def cosine_similarity(vec1, vec2):
    """Calculates cosine similarity between two numpy vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def semantic_search(query_text, top_k=3):
    """Embeds the query and searches SQLite for the most semantically similar memories."""
    import db
    
    if not client:
        return []

    try:
        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=query_text,
        )
        query_vector = response.embeddings[0].values
    except Exception as e:
        print(f"Embedding error during search: {e}")
        return []

    if not query_vector:
        return []
        
    query_np = np.array(query_vector)
    
    memories = db.get_all_vector_memories()
    if not memories:
        return []
        
    valid_memories = []
    for mem in memories:
        mem_np = np.array(mem['embedding'])
        if mem_np.shape == query_np.shape:
            mem['similarity'] = cosine_similarity(query_np, mem_np)
            valid_memories.append(mem)
        
    valid_memories.sort(key=lambda x: x['similarity'], reverse=True)
    return valid_memories[:top_k]

if __name__ == "__main__":
    print("Testing Gemini GenAI API connection...")
    result = ask("You are a helpful assistant", "Say hello")
    if result:
        print(f"Response: {result}")
    else:
        print("No response received. Ensure GEMINI_API_KEY is configured in .env and internet is connected.")
