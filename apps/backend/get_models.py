from app.llm.client import get_groq_client

def main():
    client = get_groq_client()
    for m in client.models.list().data:
        print(m.id)

if __name__ == "__main__":
    main()
