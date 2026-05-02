"""
Configuration settings, keys, and constants for Job Search OS.
"""

import os
from dotenv import load_dotenv

load_dotenv()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "your_email@gmail.com")

CANDIDATE_PROFILE = {
    "name": "Navaditya",
    "current_role": "Project Coordinator, Smartsites (US digital marketing agency)",
    "role": "Creative Project Coordinator",
    "target_roles": [
        "Creative Project Coordinator", 
        "Creative Operations Coordinator", 
        "Project Manager - Design",
        "AI Operations Manager",
        "Technical Project Manager (AI/LLM)",
        "Automation Specialist",
        "AI Integration Specialist",
        "No-code/Low-code AI Developer"
    ],
    "tracks": {
        "Track 1": "Project/Creative Operations (core strength)",
        "Track 2": "Business Analytics (growth area)",
        "Track 3": "AI Automation & Integration (differentiator)"
    },
    "skills": [
        "Project Coordination", "Creative Operations", "UI/UX Project Management", 
        "Social Media Management", "QA & Delivery", "Client Communication", 
        "Billing Management", "Agile Workflows"
    ],
    "ai_skills": [
        "AI Agent Development (Ollama, local LLMs)",
        "MCP Server Integration",
        "API Integration & Workflow Automation",
        "Prompt Engineering",
        "RAG (Retrieval Augmented Generation)",
        "Generative AI for Creative Production (video, graphics, UI/UX)",
        "Multi-model Orchestration",
        "Google Antigravity IDE"
    ],
    "ai_projects": [
        "Job Search OS — Autonomous job discovery, scoring, application writing and outreach agent using local LLMs (qwen3:8b), Gmail API, Notion API and multi-source job scraping",
        "Self-learning AI Agent — Independently built agent with memory and adaptive behavior",
        "AI Chatbot — Functional conversational bot with custom logic"
    ],
    "ai_experience_note": "Self-taught AI developer with hands-on experience building autonomous agents, MCP integrations, and LLM-powered workflows. Applied generative AI professionally for creative production at a US digital marketing agency.",
    "industries": ["Digital Marketing", "Design Agencies", "SaaS", "Creative Studios", "AI/LLM Startups"],
    "experience_years": 2,
    "education": "BBA",
    "location": "Chandigarh, India",
    "timezone": "IST (UTC+5:30)",
    "open_to_remote": True,
    "achievement": "Oversaw creative operations at a US digital marketing agency — coordinating designers, UI/UX, and video teams, conducting final QA on all deliverables, managing client relationships, and handling billing across simultaneous accounts.",
    "portfolio": "https://github.com/navr5135/portfolio",
    "github": "https://github.com/navr5135"
}
