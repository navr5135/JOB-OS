"""
Gmail Integration: Authenticates using OAuth2 and provides functions to send emails and draft follow-ups.
"""
import os
import json
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

import llm
import db

# Load environment variables
load_dotenv()

# Scopes required for the application
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = "token.json"

def get_gmail_service():
    """Authenticates and returns the Gmail API service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    elif os.getenv("GMAIL_TOKEN_JSON"):
        creds = Credentials.from_authorized_user_info(json.loads(os.environ["GMAIL_TOKEN_JSON"]), SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing Gmail tokens...")
            creds.refresh(Request())
        else:
            print(f"Loading credentials from {CREDENTIALS_FILE}...")
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Credentials file '{CREDENTIALS_FILE}' not found. Please place it in the project root.")
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"Error creating Gmail service: {e}")
        return None

def send_email(to, subject, body, cc=None):
    """Sends a plain text email to the specified recipient, optionally CC'ing others."""
    service = get_gmail_service()
    if not service:
        print("Failed to send email: Gmail service not available.")
        return False

    try:
        message = MIMEText(body)
        message['to'] = to
        if cc:
            message['cc'] = cc
        message['subject'] = subject
        
        # Base64 encode the message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': raw}
        
        # Send the message
        send_result = service.users().messages().send(userId='me', body=create_message).execute()
        print(f"Email sent successfully to {to} | Subject: {subject} | ID: {send_result['id']}")
        return True
    except HttpError as error:
        print(f"An error occurred while sending email: {error}")
        return False
    except Exception as e:
        print(f"Unexpected error in send_email: {e}")
        return False

def draft_followup(company, job_title, contact_email, job_id=None):
    """Generates a follow-up email and sends it, then updates job notes."""
    print(f"Drafting follow-up for {job_title} at {company}...")
    
    system_prompt = "Write a polite 3-sentence follow-up email for a job application. Professional tone. No subject line, just the body."
    user_message = f"Job: {job_title}\nCompany: {company}\nContact: {contact_email}"
    
    body = llm.ask_fast(system_prompt, user_message)
    
    if not body:
        print("Failed to generate follow-up body.")
        return False
        
    subject = f"Following up: {job_title} application at {company}"
    success = send_email(contact_email, subject, body)
    
    if success and job_id:
        notes = f"Follow-up sent on {os.path.basename(__file__)} to {contact_email}"
        db.update_status(job_id, 'applied', notes=notes)
        print(f"Logged follow-up in database for job {job_id}.")
        
    return success

def get_recent_emails(query="in:inbox", limit=5):
    """Fetches recent emails from Gmail via query to feed Agent context."""
    service = get_gmail_service()
    if not service:
        return ["Failed to access Gmail service."]
        
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
        messages = results.get('messages', [])
        if not messages:
            return ["No messages found matching query."]
            
        payloads = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "Unknown")
            snippet = msg_data.get('snippet', '')
            payloads.append(f"From: {sender} | Subject: {subject} | Snippet: {snippet}")
            
        return payloads
    except HttpError as error:
        return [f"Google API Error: {error}"]

if __name__ == "__main__":
    # Test block
    print("Gmail Integration Module - Test Block")
    print("Testing send_email...")
    # This will trigger OAuth flow on first run
    # Usage: python integrations/gmail.py
    # Note: User must provide email address in the next step.
