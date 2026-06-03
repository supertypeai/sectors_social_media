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

    def optimize_dividend_news(self, title, body):
        prompt = f"""
You are an expert financial news editor analyzing a dividend announcement.
Extract the key facts into a structured JSON format.

Original Title: {title}
Original Body: {body}

Extract these specific data points. If a metric is NOT explicitly mentioned in the text, you MUST output "-" for that field to prevent hallucination.
- "dividend_per_share": the dividend amount per share (e.g. 150)
- "total_dividend": the total dividend pool amount, formatted as currency (e.g. "IDR 500B", or "-").
- "cum_date": the cum-dividend date (e.g. "12 May 2026")
- "profit_metric": only the absolute amount of the profit/revenue mentioned, formatted as currency (e.g. "IDR 1T" or "IDR 50B", or "-"). Do NOT include words like "Net Profit of".
- "payout_ratio": the % of profit distributed (e.g. "50%")
- "headline": a punchy 4-6 word headline (e.g. "BBCA Announces Mega Dividend")

Return ONLY a valid JSON object matching these keys.
""".strip()
        
        try:
            response = self._chat(prompt)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"headline": title}
        except Exception as e:
            print(f"Dividend extraction error: {e}")
            return {"headline": title}

    def optimize_suspension_news(self, title, body):
        prompt = f"""
You are an expert financial news editor analyzing an IDX stock trading suspension announcement.
Extract the key facts into a structured JSON format.

Original Title: {title}
Original Body: {body}

Extract these specific data points. If a metric is NOT explicitly mentioned in the text, you MUST output "-" for that field to prevent hallucination.
- "reason": short phrase explaining why trading was suspended (e.g. "Unusual Market Activity", "Pending Material Information", "Free Float Below 7.5%"). Max 5 words.
- "effective_date": the date the suspension takes effect (e.g. "12 May 2026")
- "last_price": the last traded price before suspension, formatted as currency (e.g. "IDR 1,250")
- "expected_resumption": when trading is expected to resume (e.g. "Until Further Notice" or a specific date like "20 May 2026")
- "headline": a punchy 4-6 word headline (e.g. "BBCA Trading Suspended by IDX")

Return ONLY a valid JSON object matching these keys.
""".strip()

        try:
            response = self._chat(prompt)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"headline": title}
        except Exception as e:
            print(f"Suspension extraction error: {e}")
            return {"headline": title}

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
