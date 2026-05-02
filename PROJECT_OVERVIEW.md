# 🚀 Job Search OS: The Autonomous Personal Agent

Welcome to **Job Search OS**, a completely autonomous, locally-hosted AI assistant designed to completely automate the most frustrating parts of finding a job. 

Instead of treating AI as just a chatbot to ask questions, this project transforms AI into a **tireless digital employee that works for you 24/7**. It finds jobs, scores them against your specific skills, securely drafts cold emails to hiring managers, and chats with you over Telegram—all while running absolutely free and entirely private on your own computer hardware.

---

## 💡 The Concept: Why build this?

The traditional job hunt is broken. Spending hours scrolling through job boards, guessing if your resume matches a role, and agonizing over the perfect outreach email is exhausting. 

**Job Search OS was built to flip the script.** 

Imagine having an assistant who knows exactly what your career goals are. While you sleep, this assistant scours the internet, finds the exact roles that fit your skills, writes a personalized email to the hiring manager, and texts you on Telegram when it's done. 

Best of all? **It doesn't use the cloud.** By leveraging localized AI technology, all your data, emails, and job preferences stay completely secure on your own hard drive without paying monthly API fees to massive tech companies.

---

## 🏗️ Core Structure: How does it work?

To help anyone understand the project (even without an AI background), Job Search OS is broken down into four "Departments", just like a real company:

### 1. The Discovery & Scoring Engine (The Researcher)
Instead of manually checking job boards, this engine automatically scrapes massive remote job platforms (like Himalayas, We Work Remotely, and Remotive). 
*   **The Magic:** It doesn't just blind-apply to everything. It reads the job descriptions and uses an AI model to **"Score"** them out of 100 based on how perfectly they match *your* specific resume and skills. It acts as an aggressive filter protecting your time.

### 2. The Outreach Agent (The Publicist)
When a highly-scored job is found, this module takes action. 
*   **The Magic:** It searches the web for the company's real HR or CEO email addresses. Then, it uses AI to write a personalized, highly persuasive "cold email" explaining why you are the perfect fit for that specific role. It automatically drops the polished draft straight into your Gmail account so all you have to do is hit "Send."

### 3. The Notion Database (The Filing Cabinet)
You need to know what the AI has done.
*   **The Magic:** Every time the AI finds a job, scores it, or reaches out to a company, it syncs securely with **Notion** (a popular visual workspace app). You get a beautiful, organized dashboard showing exactly what the AI has accomplished today.

### 4. The Telegram ReAct Supervisor (The Brain)
You can directly text your AI assistant through the Telegram messaging app, securely from your phone, anywhere in the world.
*   **The Magic:** It uses a deeply advanced AI technique called **Reasoning + Acting (ReAct)**. 
    *   If you text it: *"How many jobs did we apply to today?"*, it realizes it needs to **Act**. 
    *   It silently connects to your database, counts the files, and texts you back the exact number. 
    *   If you say: *"Remember that I only like jobs with a score higher than 90,"* it uses advanced math (Vector Memory) to permanently lock that preference into its long-term memory. The next time you ask it to find jobs, it automatically applies the rule.

---

## 💻 The Tech Stack & Architecture

While the engine feels like magic, it is built on a highly optimized, fully local Python stack:

*   **Logic & Orchestration:** Pure Python 3 core managing API threading and SQLite I/O.
*   **LLM Inference Engine:** **Ollama** running fully locally (zero cloud offload).
    *   *Reasoning Model:* `qwen3:8b` (used for heavy ReAct tool-routing logic and scoring metrics).
    *   *Conversational Model:* `qwen2.5:1.5b` (used for low-latency chat and fast token generation).
*   **Vector RAG Memory:** pure mathematics via **NumPy** calculating Cosine Similarities against the `nomic-embed-text` localized embedding model.
*   **Persistence & Database:** Local **SQLite** utilizing strict JSON blob schemas and FTS (Full Text Search) structures for instant local recall.
*   **Integrations & APIs:** 
    *   **Telegram API:** Acts as the mobile command UI.
    *   **Notion API:** For visualizing the live DB pipeline via a kanban sprint board.
    *   **Gmail API (OAuth2):** Handles autonomous cold-email dispatch directly under the user's domain.
*   **Scraping & Data Gathering:** `beautifulsoup4` combined with native REST endpoints to strip remote job boards.

---

## 🌍 The Impact

Job Search OS proves that the future of Artificial Intelligence is not just about chatting—it's about **Action-Oriented Agents**. 

By orchestrating different AI models, databases, and APIs without ever leaving the user's local machine, this project demonstrates how single individuals can leverage AI to perform the workload of an entire team of assistants. 

It guarantees complete privacy, incurs zero operational costs, and changes the job search from a stressful manual grind into an elegant, automated mastery of data.
