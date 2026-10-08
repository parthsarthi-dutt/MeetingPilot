import os
import requests
import urllib.parse
from app.mcp.osint_server.pipeline import PersonOSINTPipeline
from app.mcp.osint_server.config import OSINTServerConfig

def test_osint():
    config = OSINTServerConfig.from_env()
    print(f"Jina Key loaded: {config.jina_api_key[:10]}...")
    pipeline = PersonOSINTPipeline(
        jina_api_key=config.jina_api_key,
        apify_token=config.apify_token,
        hunter_key=config.hunter_api_key,
        linkdapi_key=config.linkdapi_key,
    )
    
    print("\n--- Running Pipeline ---")
    result = pipeline.run("Rahul Pandey", "rahpande@cisco.com", "Cisco")
    print("\n--- Result ---")
    print(result)

if __name__ == "__main__":
    test_osint()
