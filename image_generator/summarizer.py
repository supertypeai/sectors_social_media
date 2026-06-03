import json
import os
import re
from urllib import parse, request
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert financial news editor.
Your goal is to make news content 'catchy' and 'snackable' for social media (Instagram/LinkedIn).
Always maintain factual accuracy while using an engaging tone.
Return ONLY the requested format."""

class NewsSummarizer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for news summarization.")

    def summarize_filing_context(self, context):
        prompt = f"""
Summarize the following financial transaction context into a very short, punchy phrase of 2 to 5 words.
Return ONLY the short phrase, nothing else.

Context: {context}
""".strip()
        
        try:
            # We don't want JSON here, just plain text
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            
            payload = {
                "system_instruction": {"parts": [{"text": "You are a concise financial editor."}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3},
            }
            
            query = parse.urlencode({"key": self.api_key})
            url = f"{endpoint}?{query}"

            req = request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with request.urlopen(req, timeout=15) as res:
                body = res.read().decode("utf-8")
                data = json.loads(body)
                summary = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Remove quotes if the LLM adds them
                summary = summary.strip('"\'')
                return summary
        except Exception as e:
            print(f"Context summarization error: {e}")
            return context[:30] + "..."

    def _chat(self, prompt):
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "response_mime_type": "application/json"},
        }
        
        query = parse.urlencode({"key": self.api_key})
        url = f"{endpoint}?{query}"

        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=30) as res:
                body = res.read().decode("utf-8")
                data = json.loads(body)
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Gemini API request failed: {e}")
