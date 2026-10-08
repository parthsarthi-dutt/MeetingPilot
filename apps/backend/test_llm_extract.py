import json
from app.llm.client import extract_attendees_with_llm

def main():
    title = "Sync on Q3 goals with Vercel team"
    description = "Let's align on the upcoming deployment pipelines."
    raw_attendees = [
        {"email": "awesome.abhi83@gmail.com", "displayName": "Abhijeet"},
        {"email": "guillermo@vercel.com", "displayName": "Guillermo Rauch"},
        {"email": "lee@vercel.com", "displayName": "Lee Robinson"},
        {"email": "john.doe@gmail.com", "displayName": "John Doe (contractor)"},
    ]
    user_email = "awesome.abhi83@gmail.com"
    
    print("Extracting attendees...")
    result = extract_attendees_with_llm(title, description, raw_attendees, user_email)
    print("Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
