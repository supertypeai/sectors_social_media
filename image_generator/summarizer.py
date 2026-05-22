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
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for news summarization.")

    def optimize_news(self, title, body):
        prompt = f"""
I have a financial news item. Please transform it for a social media post.
1. Create a 'Hook Headline': Make the title more engaging, punchy, and professional. (Max 12 words)
2. Extract 'Key Takeaways': Summarize the body into 3-4 clear, impactful bullet points. (Max 20 words per bullet)

Return ONLY a JSON object with keys "headline" and "bullets" (which is an array of strings).

Original Title: {title}
Original Body: {body}
""".strip()
        
        try:
            response = self._chat(prompt)
            # Extract JSON from potential markdown blocks
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"headline": title, "bullets": [body[:100] + "..."]}
        except Exception as e:
            print(f"Summarization error: {e}")
            return {"headline": title, "bullets": [body[:100] + "..."]}

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
