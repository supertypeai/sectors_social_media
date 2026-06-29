from dotenv import load_dotenv

from google import genai
from pydantic import BaseModel, Field 
from google.genai import types

import os
import json 


load_dotenv()


class MacroInfo(BaseModel):
    skip: bool = Field(
        description=(
            "Set true when the article covers two or more distinct macro events or topics "
            "that cannot be anchored to a single hero_value — e.g. a roundup that mentions "
            "a rate decision AND an index reclassification AND a trade deal. "
            "Set false when the article is focused on one clear event or development."
        )
    )
    direction: str = Field(
        description=(
            "The overall market direction implied by this story. "
            "Use 'up' when the story is broadly positive or bullish for Indonesian equities or the economy "
            "(e.g. rate cuts, upgrades, strong growth, trade deals, capital inflows). "
            "Use 'down' when the story is broadly negative or bearish "
            "(e.g. rate hikes, downgrades, slowdowns, sanctions, capital outflows). "
            "Must be exactly 'up' or 'down'."
        )
    )
    headline_lines: list[str] = Field(
        description=(
            "The headline split into exactly two short lines for visual rendering. "
            "Each line must be at most 40 characters. The headline must frame the "
            "story without restating hero_value — the headline sets up the anchor, "
            "hero_value delivers it. Plain sentence case, no punctuation at line end."
        )
    )
    hero_label: str | None = Field(
        description=(
            "Short UPPERCASE label identifying what hero_value represents. "
            "Examples: 'BI 7-DAY REVERSE REPO RATE', 'MSCI 2026 ACCESS REVIEW', "
            "'POWER-SECTOR COAL PRICE (DMO)'. Set null only when hero_value is null."
        )
    )
    hero_value: str | None = Field(
        description=(
            "The single most important anchor of the story shown large on the slide. "
            "Prefer a number when one clearly dominates the article (e.g. '5.75%', "
            "'$80+'). Use a short phrase of two to three words when no headline figure "
            "exists (e.g. 'Stays EM', 'Jan 2028'). Set null only when no meaningful "
            "anchor exists. When the value is numeric it must appear verbatim in the "
            "article body or title."
        )
    )
    hero_sub: str | None = Field(
        description=(
            "One supporting line beneath hero_value. Can be a change description "
            "('+100 bps in under four weeks'), a clarifier ('avoided a downgrade to "
            "frontier'), or a context qualifier ('under Law No. 4 of 2026'). "
            "Set null when nothing meaningful adds to hero_value."
        )
    )
    body: str = Field(
        description=(
            "Two to three sentences of readable narrative summarizing the macro event "
            "and its immediate market consequences. Weave secondary figures into prose "
            "rather than listing them. Written for an Indonesian retail equity investor. "
            "Do not repeat hero_value as the opening word or phrase."
        )
    )
    insight: str = Field(
        description=(
            "One sentence explaining why this macro event matters specifically for "
            "IDX investors or Indonesian equities. Lead with the consequence for "
            "investors, not a restatement of the event. Maximum 120 characters."
        )
    )


class PromptCollections:
    @staticmethod
    def system_prompt_macro_news():
        return """
            You are a financial content writer for Sectors, an Indonesian equity data
            platform. You transform a single macro news record into structured display copy
            for one social media carousel slide aimed at IDX investors.

            You will receive a record's title and body. You must return only valid JSON
            matching the provided schema, with no preamble, no markdown, and no commentary.

            CORE RULES (follow without exception):

            1. SOURCE FIDELITY. Every fact and figure in your output must come from the
            provided title or body. Do not add context, history, or numbers from outside
            the record, even if you believe them to be true. If a detail is not in the
            record, it does not exist for this task.

            2. HERO VALUE. hero_value is the single most important anchor of the story,
            shown very large on the slide.
            - Prefer a number when one figure clearly dominates the story (e.g. "5.75%",
                "US$13 billion", "Rp 200 trillion").
            - When numeric, it must appear in the title or body exactly as written there.
                Do not round, convert, restate in different units, or compute a new number.
            - Use a short phrase of two to four words only when no dominant number exists
                (e.g. "Stays EM", "New trade pact").
            - Use null only when the story has no meaningful anchor at all. Do not invent
                one to fill the slot.
            - Keep hero_value short. A long hero renders too small to read. Aim for at
                most about 14 characters.

            3. NO DUPLICATION. The headline frames the story; the hero_value delivers the
            anchor. They must not contain the same information. If the headline says
            "Bank Indonesia hiked again," the hero_value is "5.75%", not "BI rate hike."
            The body must not open by restating the headline or the hero_value.

            4. HEADLINE. Exactly two lines, each at most 40 characters, plain sentence case,
            no trailing punctuation. It states what happened in plain language without
            delivering the hero number.

            5. BODY. Two to three sentences of readable narrative prose for a retail
            investor. No bullet points. Secondary figures belong here, woven into
            sentences, not in the hero. Maximum 320 characters total.

            6. INSIGHT. One sentence, maximum 120 characters, that leads with the
            consequence for IDX investors or Indonesian equities. It explains why this
            matters, not what happened. Do not restate the event.

            7. NEUTRAL FRAMING. Report what the record states. Do not give investment
            advice, predictions, or recommendations to buy or sell. Do not editorialize
            beyond what the source supports.

            8. LANGUAGE. Write all output in English regardless of the source language.
            Preserve Indonesian proper nouns and official terms (e.g. Bank Indonesia,
            OJK, IHSG, Lembaga Penjamin Simpanan).

            9. SINGLE-EVENT FOCUS. Set skip to true when the article bundles two or more
            distinct macro events that cannot be unified under one hero_value — for example,
            a roundup that covers a rate decision, an index reclassification, and a trade
            update in the same body. A single event with supporting context is fine (skip
            remains false). When skip is true, still populate all other fields as best you
            can — the caller will discard the record automatically.

            10. DIRECTION. Set direction to "up" when the story is broadly positive or
            bullish for Indonesian equities or the economy (e.g. rate cuts, upgrades,
            strong growth, trade deals, capital inflows). Set direction to "down" when
            the story is broadly negative or bearish (e.g. rate hikes, downgrades,
            economic slowdowns, sanctions, capital outflows). The value must be exactly
            "up" or "down" — no other values are allowed.
        """
    
    @staticmethod
    def user_prompt_macro_news(title: str, body: str):
        return f""" 
            Generate slide content for the following macro news record.

            Title: {title}

            Body: {body}

            Return only valid JSON matching the required schema.
        """


class NewsSummarizer:
    MODELS = [
        "gemini-2.5-flash",
        "gemini-3-flash-preview",
        "gemini-2.5-flash-lite",
    ]

    def __init__(self):
        keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY2"),
            os.getenv("GEMINI_API_KEY3"),
        ]

        self._clients = [
            genai.Client(api_key=key) 
            for key in keys 
            if key
        ]

        if not self._clients:
            raise RuntimeError("At least one GEMINI_API_KEY is required.")

        self.prompts = PromptCollections()

    def _call(self, model: str, contents, config):
        last_error = None

        for client in self._clients:
            try:
                return client.models.generate_content(
                    model=model, 
                    contents=contents, 
                    config=config
                )
            
            except Exception as error:
                print(f"Key failed for model={model}: {error}")
                last_error = error
        
        raise last_error

    def summarize_filing_context(self, context):
        prompt = (
            "Summarize the following financial transaction context into a very short, "
            "punchy phrase of 2 to 5 words. Return ONLY the short phrase.\n\n"
            f"Context: {context}"
        )
       
        for model in self.MODELS:
            try:
                print(f'model used: {model}')

                resp = self._call(
                    model=model,
                    contents=prompt,
                    config={
                        "temperature": 0.3,
                        "system_instruction": "You are a concise financial editor.",
                    },
                )

                return (resp.text or "").strip().strip('"\'')
            
            except Exception as error:
                print(f"Context summarization error for model={model}: {error}")

        print(f"All models and keys failed for: {str(context)[:60]}")
        return str(context)[:30] + "..."
    
    def generate_macro_slide(self, title: str, body: str, tags: list[str]):
        system_prompt = self.prompts.system_prompt_macro_news()
        user_prompt = self.prompts.user_prompt_macro_news(title, body)
        
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type='application/json',
            response_schema=MacroInfo,
            temperature=0.4
        )

        for model in self.MODELS:
            try:
                print(f'model used: {model}')

                response = self._call(
                    model=model, 
                    contents=user_prompt, 
                    config=config
                )

                result = json.loads(response.text)

                if result.get('skip'):
                    print(f"Skipping multi-event article: {title[:60]}")
                    return None

                result['category_pill'] = tags[0] if tags else "MACRO"
                return result

            except Exception as error:
                print(f"All keys exhausted for model={model}: {error}")

        print(f"All models and keys failed for: {title[:60]}")
        return None
