"""
Test Gmail Integration: Sends a test email to verify the Gmail integration.
"""
import sys
import os
# Add the project root to sys.path to allow importing from integrations
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.gmail import send_email

def main():
    print("Welcome to the Job Search OS Gmail Test")
    print("---------------------------------------")
    
    # We will let the user provide the email address during execution
    # But since this is a script, we can ask for it or take it as an argument
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = input("Enter the Gmail address to send the test email to: ")
    
    print(f"Sending test email to: {recipient}")
    subject = "Job Search OS - Gmail Test"
    body = "Gmail integration is working!"
    
    success = send_email(recipient, subject, body)
    
    if success:
        print("\nSUCCESS: Test email sent.")
    else:
        print("\nFAILURE: Could not send test email.")

if __name__ == "__main__":
    main()
