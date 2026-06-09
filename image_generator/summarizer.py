import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


class NewsSummarizer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for news summarization.")
        self._client = genai.Client(api_key=self.api_key)

    def summarize_filing_context(self, context):
        prompt = (
            "Summarize the following financial transaction context into a very short, "
            "punchy phrase of 2 to 5 words. Return ONLY the short phrase.\n\n"
            f"Context: {context}"
        )
        try:
            resp = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": 0.3,
                    "system_instruction": "You are a concise financial editor.",
                },
            )
            return (resp.text or "").strip().strip('"\'')
        except Exception as e:
            print(f"Context summarization error: {e}")
            return str(context)[:30] + "..."
