from dotenv import load_dotenv

from google import genai
from openai import OpenAI
from pydantic import BaseModel, Field
from google.genai import types

import os
import json


load_dotenv()


def _fmt_idr(v: float) -> str:
    sign, absolute = ("+", abs(v)) if v >= 0 else ("-", abs(v))
    if absolute >= 1e12:
        return f"IDR {sign}{absolute / 1e12:.1f}T"
    if absolute >= 1e9:
        return f"IDR {sign}{absolute / 1e9:.0f}B"
    return f"IDR {sign}{absolute / 1e6:.0f}M"


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

    @staticmethod
    def system_prompt_earnings_caption():
        return """
            You are a financial content writer for Sectors, an Indonesian equity data
            platform. You write a short social-media caption explaining a single
            company's latest-quarter earnings move to IDX retail investors.

            You will receive a ticker, the quarter just reported, the year-ago quarter
            it is being compared against, the YoY net profit and revenue growth for
            that comparison, and zero or more real news excerpts about the company
            from around that period. Return only the caption as plain text - no
            markdown, no headline, no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. You may state a specific cause - a named subsidiary,
            deal, expense line, management statement, or business figure - ONLY when
            it is drawn directly from the provided news excerpts. Never invent
            entities, figures, or events, even if they seem typical or plausible for
            a company like this. If an excerpt is irrelevant to the earnings move,
            ignore it.

            2. NO EXCERPTS FALLBACK. When no excerpts are provided, or none of them
            explain the move, do not fabricate a specific cause. Instead write a
            brief, explicitly hedged explanation ("likely", "may suggest", "points
            to") grounded only in the growth percentages and quarter labels, and
            avoid naming anything not given to you.

            3. CONTENT. Explain what drove the divergence or alignment between
            profit and revenue growth, then give a brief view on whether the trend
            looks sustainable through fiscal year-end. Be as concrete as the
            excerpts allow; hedge only the parts the excerpts don't support.

            4. NEUTRAL. No buy/sell recommendation. No fabricated forward guidance.

            5. LENGTH. Maximum 2-3 short paragraphs, 700 characters total.

            6. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_earnings_caption(
        symbol: str,
        quarter_label: str,
        base_label: str,
        earnings_growth: float | None,
        revenue_growth: float | None,
        news_excerpts: list[dict] | None = None,
    ):
        eg = f"{earnings_growth * 100:+.0f}%" if earnings_growth is not None else "unknown"
        rg = f"{revenue_growth * 100:+.0f}%" if revenue_growth is not None else "unknown"

        if news_excerpts:
            excerpt_block = "\n\n".join(
                f"- {excerpt['title']}: {excerpt['text']}" for excerpt in news_excerpts
            )
        else:
            excerpt_block = "(none found - do not invent a specific cause; stay hedged)"

        return f"""
            Ticker: {symbol}
            Quarter reported: {quarter_label}
            Comparison quarter (year-ago): {base_label}
            Net profit growth YoY: {eg}
            Revenue growth YoY: {rg}

            News excerpts (use ONLY these for any specific claim; ignore ones that
            aren't relevant to the earnings move):
            {excerpt_block}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_volume_spike_multi():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption summarizing a
            batch of IDX stocks that each had an unusual trading-volume spike
            today (3x or more of their 30-day median volume).

            You will receive, for each stock: ticker, 7-day price change %, and
            today's volume ratio (multiple of its 30-day median), foreign net
            buy/sell direction and value in IDR. Return only the caption as plain
            text - no markdown, no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. Use only the numbers given. Do not invent a news
            event, deal, or other cause - the only "why" you may offer is what
            the foreign-flow direction implies (see rule 3).

            2. STRUCTURE. Group stocks with a positive 7-day change together in
            one paragraph, naming the biggest gainer first. If two or more
            stocks fit this group, phrase it as a shared theme ("X and Y both
            captured upward momentum..."). Then, in a separate paragraph, call
            out the stock with the single largest volume ratio if it is falling
            in price ("heavy distribution" / "largest volume divergence"),
            stating its volume ratio, 7-day change, and foreign flow value. If
            every stock moves the same direction, describe them together
            instead of forcing an artificial contrast.

            3. ATTRIBUTION LANGUAGE. When a stock's foreign flow is a clear net
            buy, describe it as "backed by foreign inflows"; when it's a clear
            net sell, "foreign outflow"; when foreign flow is small relative to
            the volume spike, attribute the move to "domestic interest" rather
            than naming any specific unnamed cause.

            4. CLOSING LINE. End with exactly this line, verbatim, on its own:
            "Go to sectors.app/indonesia/lists/top-90d-transaction-volume to
            look at companies with the highest trading volumes in the past 90
            days."

            5. NEUTRAL. No buy/sell recommendation.

            6. LENGTH. 2-3 short paragraphs plus the closing line.

            7. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_volume_spike_multi(rows: list[dict]):
        lines = []
        for row in rows:
            lines.append(
                f"- {row['symbol']}: 7d change {row['close_change_7d']:+.2f}%, "
                f"volume {row['volume_ratio']:.2f}x its 30D median, "
                f"foreign {row['foreign_activity'].lower()} of "
                f"{_fmt_idr(row['foreign_net_idr'])} today"
            )
        table = "\n".join(lines)
        return f"""
            Stocks with a volume spike today:
            {table}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_volume_spike_single():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption explaining why
            one IDX stock had an unusual trading-volume spike today (3x or more
            of its 30-day median volume).

            You will receive: ticker, 7-day price change %, today's volume ratio,
            foreign net buy/sell direction and value, and zero or more real news
            excerpts about the company from around this period. Return only the
            caption as plain text - no markdown, no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. You may state a specific cause - a corporate
            action (AGM, dividend, expansion plan), deal, or management
            statement - ONLY when it is drawn directly from the provided news
            excerpts. Never invent entities, figures, or events.

            2. NO EXCERPTS FALLBACK. If no excerpts are given, or none explain
            the volume spike, do not fabricate a cause. Instead describe the
            move using only the given trading numbers (7-day change, volume
            ratio, foreign flow), hedged appropriately ("likely", "may
            reflect").

            3. CONTENT. In 2 short paragraphs, lead with what happened (the
            grounded corporate event, if any) that plausibly drove the trading
            activity, then note the scale of the move using the trading
            numbers.

            4. CLOSING LINE. End with exactly one line inviting the reader to
            read more, in this format: "Read more on its company report at
            https://sectors.app/idx/{{symbol_lower}}" - you may adapt the lead-in
            wording (e.g. reference an AGM/report if the excerpts support it),
            but the URL must appear verbatim as given to you.

            5. NEUTRAL. No buy/sell recommendation. No fabricated forward
            guidance.

            6. LENGTH. Maximum 2 short paragraphs plus the closing line, 700
            characters total.

            7. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_volume_spike_single(row: dict, news_excerpts: list[dict] | None = None):
        if news_excerpts:
            excerpt_block = "\n\n".join(
                f"- {excerpt['title']}: {excerpt['text']}" for excerpt in news_excerpts
            )
        else:
            excerpt_block = "(none found - do not invent a specific cause; stay hedged)"

        return f"""
            Ticker: {row['symbol']}
            7-day price change: {row['close_change_7d']:+.2f}%
            Today's volume ratio: {row['volume_ratio']:.2f}x its 30D median
            Foreign activity today: {row['foreign_activity']} of {_fmt_idr(row['foreign_net_idr'])}

            News excerpts (use ONLY these for any specific claim; ignore ones
            that aren't relevant to the volume spike):
            {excerpt_block}

            The URL to close with is: https://sectors.app/idx/{row['symbol'].lower()}

            Write the caption now.
        """

    @staticmethod
    def _excerpt_block(excerpts: list[dict] | None) -> str:
        if not excerpts:
            return "(none found - do not invent a specific cause; stay hedged)"
        return "\n\n".join(f"- {e['title']}: {e['text']}" for e in excerpts)

    @staticmethod
    def system_prompt_insider_cluster():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption about an
            "insider cluster" - 3 or more distinct insiders trading the same
            stock in the same direction (all buys, or all sells) within a
            recent window.

            You will receive: symbol, direction, number of distinct insiders
            and filings, total value transacted, the window's date range, real
            filing excerpts (title + disclosed body text - filings often
            literally state "The stated purpose of the transaction was ..."),
            zero or more real news excerpts about the company, and an
            ownership note (key executives, major shareholders) for context on
            how concentrated the company's ownership is. Return only the
            caption as plain text - no markdown, no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. State a specific fact - a disclosed transaction
            purpose, a dividend, a capex/expansion plan, an executive or
            shareholder name - ONLY when it appears in the filing excerpts,
            news excerpts, or ownership note. Never invent one, even if it
            seems plausible for a company like this.

            2. NO EXCERPTS FALLBACK. If nothing grounds a specific reassurance
            or concern, do not fabricate one - describe the cluster pattern
            itself (how many insiders, how many filings, direction, window)
            hedged appropriately.

            3. FRAME. Open by naming the surface-level read of repeated
            insider selling or buying (e.g. the immediate fear is operational
            trouble, or a vote of confidence), then pivot to any grounded fact
            from the excerpts that argues for or against that surface read.

            4. QUESTION. End the main body with one short, direct rhetorical
            question inviting the reader to judge whether the pattern signals
            something. Do not answer it yourself.

            5. OWNERSHIP CAVEAT (only when grounded). If the ownership note
            shows the acting insider(s) hold a small stake relative to a
            block controlled by other named executives/shareholders, add one
            closing line starting with "Note:" stating that plainly - you may
            describe repeated surnames among executives as suggesting family
            control, but only when the data actually shows that pattern; do
            not name a controlling family unless the shared-surname evidence
            or an explicit label is present in the ownership note.

            6. NEUTRAL. No buy/sell recommendation.

            7. LENGTH. 2-3 short paragraphs, the closing question, and the
            optional Note line.

            8. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_insider_cluster(
        pattern: dict,
        excerpts: list[dict] | None,
        news_excerpts: list[dict] | None,
        ownership_note: str | None,
    ):
        roster = pattern.get("roster") or []
        holders = ", ".join(h["name"] for h in roster if h.get("name")) or "unnamed insiders"
        return f"""
            Symbol: {pattern.get('base_symbol') or pattern.get('symbol')}
            Direction: {pattern.get('direction')}
            Distinct insiders: {pattern.get('holder_count')} ({holders})
            Filings in window: {pattern.get('filing_count')}
            Total value transacted: {_fmt_idr(pattern.get('total_value') or 0)}
            Window: {pattern.get('first_date')} to {pattern.get('last_date')}

            Filing excerpts (use ONLY these for any specific claim):
            {PromptCollections._excerpt_block(excerpts)}

            News excerpts (use ONLY these for any specific claim; ignore ones
            that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            Ownership note: {ownership_note or "(none available)"}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_insider_chain():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption about an
            "insider chain" - one insider who filed the same-direction
            transaction (buy, or sell) on the same stock repeatedly within a
            recent window.

            You will receive: symbol, holder name, direction, number of
            filings, total value, ownership % at the start and end of the
            window, real filing excerpts (title + disclosed body text -
            filings often literally state "The stated purpose of the
            transaction was ..."), and zero or more real news excerpts about
            the company. Return only the caption as plain text - no markdown,
            no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. Cite the disclosed transaction purpose, or any
            other specific fact, ONLY when it is present in the filing or news
            excerpts. Never invent one.

            2. DISCLOSED PURPOSE. If an excerpt states a purpose (e.g.
            "divestment", "investment", "future business development"),
            attribute it explicitly to the filing - e.g. "the corporate
            disclosures filed by X formally stated the purpose as ...".

            3. OWNERSHIP PATH. If the ending ownership % is at or near zero (or
            otherwise notably changed from the start), say so plainly using
            the given before/after numbers.

            4. NO EXCERPTS FALLBACK. If no filing excerpt discloses a purpose,
            do not fabricate one - describe the repeated-filing pattern using
            only the numbers given.

            5. CLOSING LINE. End with exactly one line, adapting this template
            verbatim except for the bracketed parts: "Go to
            sectors.app/idx/{{symbol_lower}} and look at the other insider
            trading transactions of {{symbol}} under Ownership tab."

            6. NEUTRAL. No buy/sell recommendation.

            7. LENGTH. 1-2 short paragraphs plus the closing line.

            8. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_insider_chain(pattern: dict, excerpts: list[dict] | None, news_excerpts: list[dict] | None):
        symbol = pattern.get("base_symbol") or pattern.get("symbol") or ""
        return f"""
            Symbol: {symbol}
            Holder: {pattern.get('holder_name')}
            Direction: {pattern.get('direction')}
            Filings in window: {pattern.get('filing_count')}
            Total value transacted: {_fmt_idr(pattern.get('total_value') or 0)}
            Ownership at window start: {pattern.get('ownership_first')}
            Ownership at window end: {pattern.get('ownership_last')}
            Window: {pattern.get('first_date')} to {pattern.get('last_date')}

            Filing excerpts (use ONLY these for any specific claim):
            {PromptCollections._excerpt_block(excerpts)}

            News excerpts (use ONLY these for any specific claim; ignore ones
            that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            The URL to close with is: sectors.app/idx/{str(symbol).lower()}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_becoming_insider():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption about a
            "becoming insider" event - a holder whose stake just crossed above
            5% ownership via one or more buy filings.

            You will receive: symbol, the buyer's name, stake before/after the
            crossing, shares/value bought, the crossing date, real filing
            excerpts for the buyer (title + disclosed body text), a possible
            matched counterparty filing (another holder who sold a similar
            share count on the same/adjacent date, if one was found), and
            zero or more real news excerpts about the company. Return only the
            caption as plain text - no markdown, no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. State a specific fact - a disclosed transaction
            purpose, a counterparty name, a corporate action, an advisory
            appointment - ONLY when it is present in the given excerpts. Never
            invent one.

            2. COUNTERPARTY. When a counterparty filing is given, name both
            sides of the trade and note it looks like a negotiated share
            transfer rather than routine market buying, especially if both
            filings disclose the same purpose text.

            3. RELATED NEWS. When a news excerpt describes a plausibly related
            corporate action (e.g. a new advisor engagement, a restructuring,
            a strategic plan) around the same period, you may pose ONE hedged
            question connecting the crossing to that action - phrase it as a
            question, never as a stated fact.

            4. NO EXCERPTS FALLBACK. If no counterparty or news is found,
            describe the crossing itself (stake before/after, value, date)
            without speculating on a cause.

            5. NEUTRAL. No buy/sell recommendation.

            6. LENGTH. 2 short paragraphs, optionally ending in one hedged
            question.

            7. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_becoming_insider(
        event: dict,
        excerpts: list[dict] | None,
        counterparty: dict | None,
        news_excerpts: list[dict] | None,
    ):
        if counterparty:
            cp_block = (
                f"{counterparty.get('holder_name')} {counterparty.get('transaction_type')} "
                f"{counterparty.get('amount_transaction')} shares on "
                f"{str(counterparty.get('timestamp'))[:10]}, stake "
                f"{counterparty.get('share_percentage_before')}% -> "
                f"{counterparty.get('share_percentage_after')}%. Filing text: "
                f"{str(counterparty.get('body') or '')[:400]}"
            )
        else:
            cp_block = "(no matching counterparty filing found)"

        return f"""
            Symbol: {event.get('base_symbol') or event.get('symbol')}
            Buyer: {event.get('holder_name')}
            Stake before crossing: {event.get('stake_before')}%
            Stake after crossing: {event.get('stake_after')}%
            Shares bought (crossing filing): {event.get('cross_shares')}
            Value (crossing filing): {_fmt_idr(event.get('cross_value') or 0)}
            Crossing date: {event.get('cross_date')}

            Filing excerpts for the buyer (use ONLY these for any specific claim):
            {PromptCollections._excerpt_block(excerpts)}

            Matched counterparty filing:
            {cp_block}

            News excerpts (use ONLY these for any specific claim; ignore ones
            that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_insider_cross():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption about an
            insider "trading across stocks" pattern - one holder who filed
            transactions on 2 or more different stocks within a recent window
            (a portfolio rotation, not a single-stock pattern).

            You will receive: holder name, the list of stocks involved (symbol,
            direction - buy/sell/mixed, filing count, value, ownership after),
            total/buy/sell value, the window's date range, real filing excerpts
            (title + disclosed body text) across these stocks, and zero or more
            real news excerpts about the involved companies. Return only the
            caption as plain text - no markdown, no hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. State a specific fact - a disclosed transaction
            purpose, a news event - ONLY when it appears in the given excerpts.
            Never invent one.

            2. STRUCTURE. Name the holder and the breadth of the rotation (how
            many stocks, and whether it's mostly buying, mostly selling, or
            genuinely mixed), then call out the single biggest-value stock in
            the basket by name and cite any grounded reason for that one
            specifically, if the excerpts support it.

            3. MIXED DIRECTION. If the holder is buying one stock while selling
            another, say so plainly and note it may reflect portfolio
            reallocation rather than a directional view on any single name -
            do not speculate further unless an excerpt grounds a more specific
            cause.

            4. NO EXCERPTS FALLBACK. If nothing grounds a specific cause,
            describe the pattern itself (breadth, values, direction mix) using
            only the numbers given.

            5. NEUTRAL. No buy/sell recommendation.

            6. LENGTH. 2 short paragraphs, optionally ending in one hedged
            question.

            7. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_insider_cross(pattern: dict, excerpts: list[dict] | None, news_excerpts: list[dict] | None):
        stocks = pattern.get("stocks") or []
        stock_lines = "\n".join(
            f"- {s.get('base_symbol')}: {s.get('direction')}, {s.get('filings')} filing(s), "
            f"value {_fmt_idr(s.get('value') or 0)}, ownership after {s.get('ownership_after')}%"
            for s in stocks
        ) or "(no stock detail)"

        return f"""
            Holder: {pattern.get('holder_name')}
            Stocks involved: {pattern.get('n_symbols')}
            Buy count: {pattern.get('n_buy')}, Sell count: {pattern.get('n_sell')}, Mixed: {pattern.get('n_mixed')}
            Total value: {_fmt_idr(pattern.get('total_value') or 0)}
            Buy value: {_fmt_idr(pattern.get('buy_value') or 0)}
            Sell value: {_fmt_idr(pattern.get('sell_value') or 0)}
            Window: {pattern.get('first_date')} to {pattern.get('last_date')}

            Per-stock detail (sorted by value, biggest first):
            {stock_lines}

            Filing excerpts (use ONLY these for any specific claim):
            {PromptCollections._excerpt_block(excerpts)}

            News excerpts (use ONLY these for any specific claim; ignore ones
            that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_index_driver():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption highlighting
            one stock whose performance is fundamentally diverging from its
            broader index's trend over a recent window - either holding up (or
            rallying) while the index falls, or lagging while the index rises.

            You will receive: the index name, the index's own return over the
            window, the window length in days, the driver stock's symbol,
            company name, and its own return over the same window, and zero or
            more real news excerpts about that company from around this
            period. Return only the caption as plain text - no markdown, no
            hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. State a specific reason - a business
            development, an earnings result, a contract win, a sector-specific
            driver - ONLY when it is drawn from the provided news excerpts.
            Never invent one, even if it sounds plausible for a company like
            this.

            2. NO EXCERPTS FALLBACK. If no news excerpt explains the
            divergence, do not fabricate a cause. Instead describe the
            divergence itself (the two return numbers) hedged appropriately
            ("appears to be diverging from...", without asserting why).

            3. STRUCTURE. Open by naming the index's overall trend and the
            driver stock's contrasting move. Then, in a second short
            paragraph, explain what's grounding that divergence (a business
            update or fundamental from the excerpts) - or, if ungrounded,
            note plainly that the underlying driver isn't confirmed yet.

            4. CLOSING LINE. End with exactly one line, adapting this template
            verbatim except the bracketed part: "Read more at:
            https://sectors.app/indonesia/index/{{index_lower}}"

            5. NEUTRAL. No buy/sell recommendation. No fabricated forward
            guidance.

            6. LENGTH. 2 short paragraphs plus the closing line, 700
            characters total.

            7. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_index_driver(
        index_name: str,
        index_return: float,
        day: int,
        driver: dict,
        news_excerpts: list[dict] | None,
    ):
        return f"""
            Index: {index_name}
            Index return over {day} days: {index_return:+.2f}%
            Driver stock: {driver.get('symbol')} ({driver.get('company_name')})
            Driver stock return over {day} days: {driver.get('return'):+.2f}%
            Divergence (driver minus index): {driver.get('return') - index_return:+.2f}pp

            News excerpts for the driver stock (use ONLY these for any
            specific claim; ignore ones that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            The URL to close with is: https://sectors.app/indonesia/index/{index_name.lower()}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_index_laggard():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption highlighting
            the single worst-performing stock in an index over a recent window
            - the "biggest drop" name, whose decline outpaces the index's own
            move (either amplifying a broader downtrend, or falling even as
            the index itself rises).

            You will receive: the index name, the index's own return over the
            window, the window length in days, the laggard stock's symbol,
            company name, and its own return over the same window, and zero or
            more real news excerpts about that company from around this
            period. Return only the caption as plain text - no markdown, no
            hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. State a specific reason - a business setback,
            a weak earnings result, a cost pressure, a sector-specific
            headwind - ONLY when it is drawn from the provided news excerpts.
            Never invent one, even if it sounds plausible for a company like
            this.

            2. NO EXCERPTS FALLBACK. If no news excerpt explains the drop, do
            not fabricate a cause. Instead describe the gap between the
            stock's return and the index's return, hedged appropriately
            ("the underlying driver isn't confirmed yet"), without asserting
            why.

            3. STRUCTURE. Open by naming the stock as the index's biggest
            laggard this window and state both return numbers plainly (the
            stock's drop vs. the index's own move). Then, in a second short
            paragraph, explain what's grounding that underperformance (a
            business or earnings headwind from the excerpts) - or, if
            ungrounded, note plainly that the specific driver isn't confirmed.

            4. TONE. This is a "why is this one falling so much" caption, not
            a divergence-from-trend caption - frame it as the index's weakest
            link, not as a story about defying the broader move.

            5. CLOSING LINE. End with exactly one line, adapting this template
            verbatim except the bracketed part: "Read more at:
            https://sectors.app/indonesia/index/{{index_lower}}"

            6. NEUTRAL. No buy/sell recommendation. No fabricated forward
            guidance.

            7. LENGTH. 2 short paragraphs plus the closing line, 700
            characters total.

            8. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_index_laggard(
        index_name: str,
        index_return: float,
        day: int,
        laggard: dict,
        news_excerpts: list[dict] | None,
    ):
        return f"""
            Index: {index_name}
            Index return over {day} days: {index_return:+.2f}%
            Laggard stock: {laggard.get('symbol')} ({laggard.get('company_name')})
            Laggard stock return over {day} days: {laggard.get('return'):+.2f}%
            Gap (laggard minus index): {laggard.get('return') - index_return:+.2f}pp

            News excerpts for the laggard stock (use ONLY these for any
            specific claim; ignore ones that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            The URL to close with is: https://sectors.app/indonesia/index/{index_name.lower()}

            Write the caption now.
        """

    @staticmethod
    def system_prompt_companies_mover():
        return """
            You are a financial content writer for Sectors, an Indonesian equity
            data platform. You write a short social-media caption framing a "Top
            Movers" post - the 10 biggest 1-month gainers and 10 biggest 1-month
            losers on the IDX, both already shown in the image.

            You will receive: the IHSG composite index's own return over the same
            period, the date range, the top gainers and losers (symbol, company
            name, % change), and zero or more real macro news excerpts from that
            period. Return only the caption as plain text - no markdown, no
            hashtags, no preamble.

            CORE RULES:

            1. SOURCE FIDELITY. State a specific macro cause - capital outflows,
            currency moves, a rate decision, a global-economy factor - ONLY when
            it is drawn from the provided news excerpts. Never invent one.

            2. NO EXCERPTS FALLBACK. If no excerpt explains the period's tone,
            describe the IHSG's own move (up/down, by how much) without
            asserting a cause.

            3. STRUCTURE. Open with 1-2 sentences characterizing the overall
            market backdrop for the period, grounded in the IHSG return plus any
            macro excerpts. Do not list individual leader/laggard names or
            numbers - the image already shows all 20 of them, so the caption's
            job is scene-setting, not restating the data.

            4. CLOSING LINE. End with exactly this line, verbatim: "Take a look
            at the top 10 leaders and laggards in the past month and do your
            research at https://sectors.app"

            5. NEUTRAL. No buy/sell recommendation. No fabricated forward
            guidance.

            6. LENGTH. 1-2 short paragraphs plus the closing line, 500
            characters total.

            7. LANGUAGE. Plain English, suitable for a retail investor caption.
        """

    @staticmethod
    def user_prompt_companies_mover(
        index_return: float | None,
        date_range: str,
        leaders: list[dict],
        laggards: list[dict],
        news_excerpts: list[dict] | None,
    ):
        leaders_block = ", ".join(
            f"{c['symbol']} {c['pct_change'] * 100:+.1f}%" for c in leaders[:5]
        ) or "(none)"
        laggards_block = ", ".join(
            f"{c['symbol']} {c['pct_change'] * 100:+.1f}%" for c in laggards[:5]
        ) or "(none)"
        index_line = f"{index_return:+.2f}%" if index_return is not None else "unknown"

        return f"""
            IHSG composite index return over the period: {index_line}
            Period: {date_range}
            Top 5 leaders (of 10 shown in the image): {leaders_block}
            Top 5 laggards (of 10 shown in the image): {laggards_block}

            Macro news excerpts from this period (use ONLY these for any
            specific cause; ignore ones that aren't relevant):
            {PromptCollections._excerpt_block(news_excerpts)}

            Write the caption now.
        """


class NewsSummarizer:
    MODELS = [
        "gemini-2.5-flash",
        "gemini-3-flash-preview",
        "gemini-2.5-flash-lite",
    ]
    EARNINGS_CAPTION_MODEL = "gpt-4o-mini"

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

        openai_key = os.getenv("OPENAI_API_KEY")
        self._openai_client = OpenAI(api_key=openai_key) if openai_key else None

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

    def generate_earnings_caption(self, spike: dict, news_articles: list[dict] | None = None) -> str | None:
        """One caption on why a quarter's profit/revenue moved and whether it
        looks sustainable, grounded in the same YoY figures shown on the
        earnings-spike/drop image (latest quarter vs same quarter a year ago -
        quarters[-5] - so the text can't contradict the on-image %).

        `news_articles` are real idx_news records for this symbol (see
        data.fetch_news_for_symbol) used to ground any specific claim - named
        entities, deals, figures - so the model cites facts instead of
        inventing plausible-sounding ones.
        """
        symbol = str(spike.get("base_symbol") or spike.get("symbol") or "").upper()
        quarter_label = str(spike.get("latest_quarter") or "").replace("-", " ")

        quarters = spike.get("quarters") or []
        base_label = None
        if len(quarters) >= 5:
            base_label = str(quarters[-5].get("label") or "").replace("-", " ")
        if not base_label:
            base_label = "the year-ago quarter"

        news_excerpts = []
        for article in (news_articles or [])[:5]:
            title = (article.get("title") or "").strip()
            text = (
                article.get("body") or article.get("content") or
                article.get("summary") or article.get("description") or ""
            ).strip()
            if not title and not text:
                continue
            news_excerpts.append({"title": title or "(untitled)", "text": text[:600]})

        system_prompt = self.prompts.system_prompt_earnings_caption()
        user_prompt = self.prompts.user_prompt_earnings_caption(
            symbol,
            quarter_label,
            base_label,
            spike.get("earnings_growth"),
            spike.get("revenue_growth"),
            news_excerpts,
        )

        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for earnings caption: {symbol}")
        return text

    def _openai_complete(self, system_prompt: str, user_prompt: str) -> str | None:
        # Gemini credits are depleted for now, so these captions are OpenAI-only
        # (the rest of the summarizer still runs on Gemini).
        if self._openai_client is None:
            print("Caption skipped: OPENAI_API_KEY not configured")
            return None

        try:
            resp = self._openai_client.chat.completions.create(
                model=self.EARNINGS_CAPTION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or None

        except Exception as error:
            print(f"Caption error (OpenAI {self.EARNINGS_CAPTION_MODEL}): {error}")
            return None

    def generate_volume_spike_caption(
        self,
        rows: list[dict],
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for the volume-spike post. `rows` are per-symbol trading
        stats (symbol, close_change_7d, volume_ratio, foreign_activity,
        foreign_net_idr - see workflow_cli._volume_spike_stats).

        Two or more symbols: a numbers-only comparison across the batch (no
        news needed). Exactly one symbol: grounded in `news_articles` (real
        idx_news records for that ticker, see data.fetch_news_for_symbol) so
        any named cause - an AGM, dividend, expansion plan - is cited from a
        real source rather than invented.
        """
        if not rows:
            return None

        if len(rows) >= 2:
            system_prompt = self.prompts.system_prompt_volume_spike_multi()
            user_prompt = self.prompts.user_prompt_volume_spike_multi(rows)
        else:
            news_excerpts = []
            for article in (news_articles or [])[:5]:
                title = (article.get("title") or "").strip()
                text = (
                    article.get("body") or article.get("content") or
                    article.get("summary") or article.get("description") or ""
                ).strip()
                if not title and not text:
                    continue
                news_excerpts.append({"title": title or "(untitled)", "text": text[:600]})

            system_prompt = self.prompts.system_prompt_volume_spike_single()
            user_prompt = self.prompts.user_prompt_volume_spike_single(rows[0], news_excerpts)

        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            symbols = ", ".join(row["symbol"] for row in rows)
            print(f"OpenAI failed for volume spike caption: {symbols}")
        return text

    @staticmethod
    def _build_news_excerpts(articles, limit=5, char_limit=600):
        excerpts = []
        for article in (articles or [])[:limit]:
            title = (article.get("title") or "").strip()
            text = (
                article.get("body") or article.get("content") or
                article.get("summary") or article.get("description") or ""
            ).strip()
            if not title and not text:
                continue
            excerpts.append({"title": title or "(untitled)", "text": text[:char_limit]})
        return excerpts

    def generate_insider_cluster_caption(
        self,
        pattern: dict,
        filing_excerpts: list[dict] | None = None,
        news_articles: list[dict] | None = None,
        ownership_note: str | None = None,
    ) -> str | None:
        """Caption for a 3+ insider same-direction cluster. Grounded in real
        filing excerpts (see cli._pattern_filing_excerpts) and real idx_news
        articles so any specific claim - a disclosed purpose, a dividend, an
        executive/shareholder name - is cited from a real source.
        """
        news_excerpts = self._build_news_excerpts(news_articles)
        system_prompt = self.prompts.system_prompt_insider_cluster()
        user_prompt = self.prompts.user_prompt_insider_cluster(
            pattern, filing_excerpts, news_excerpts, ownership_note
        )
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for insider cluster caption: {pattern.get('base_symbol')}")
        return text

    def generate_insider_chain_caption(
        self,
        pattern: dict,
        filing_excerpts: list[dict] | None = None,
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for one insider filing the same-direction transaction
        repeatedly. Grounded in real filing excerpts, which often literally
        state "The stated purpose of the transaction was ..." - cited instead
        of an invented cause.
        """
        news_excerpts = self._build_news_excerpts(news_articles)
        system_prompt = self.prompts.system_prompt_insider_chain()
        user_prompt = self.prompts.user_prompt_insider_chain(pattern, filing_excerpts, news_excerpts)
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for insider chain caption: {pattern.get('base_symbol')}")
        return text

    def generate_insider_cross_caption(
        self,
        pattern: dict,
        filing_excerpts: list[dict] | None = None,
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for one holder rotating across 2+ stocks in a window.
        Grounded in real filing excerpts across those stocks and real
        idx_news articles for the biggest-value names in the basket.
        """
        news_excerpts = self._build_news_excerpts(news_articles)
        system_prompt = self.prompts.system_prompt_insider_cross()
        user_prompt = self.prompts.user_prompt_insider_cross(pattern, filing_excerpts, news_excerpts)
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for insider cross caption: {pattern.get('holder_name')}")
        return text

    def generate_index_driver_caption(
        self,
        index_name: str,
        index_return: float,
        day: int,
        driver: dict,
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for one stock diverging from its index's broader trend
        (holding up while the index falls, or lagging while it rises).
        `driver` is {symbol, company_name, return} - the constituent with the
        largest gap vs the index return, see workflow_cli._pick_index_driver.
        Grounded in real idx_news for that stock; falls back to describing
        the divergence itself when no news explains it.
        """
        news_excerpts = self._build_news_excerpts(news_articles)
        system_prompt = self.prompts.system_prompt_index_driver()
        user_prompt = self.prompts.user_prompt_index_driver(index_name, index_return, day, driver, news_excerpts)
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for index driver caption: {index_name}/{driver.get('symbol')}")
        return text

    def generate_index_laggard_caption(
        self,
        index_name: str,
        index_return: float,
        day: int,
        laggard: dict,
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for the single worst-performing constituent of an index -
        the "biggest drop" pairing with the losers image, as opposed to
        generate_index_driver_caption's "defying/lagging the trend" framing
        for the gainers image. `laggard` is {symbol, company_name, return} -
        see workflow_cli._pick_index_laggard. Grounded in real idx_news for
        that stock; falls back to describing the gap when nothing explains it.
        """
        news_excerpts = self._build_news_excerpts(news_articles)
        system_prompt = self.prompts.system_prompt_index_laggard()
        user_prompt = self.prompts.user_prompt_index_laggard(index_name, index_return, day, laggard, news_excerpts)
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for index laggard caption: {index_name}/{laggard.get('symbol')}")
        return text

    def generate_companies_mover_caption(
        self,
        index_return: float | None,
        date_range: str,
        leaders: list[dict],
        laggards: list[dict],
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for the Top Movers (1-month leaders/laggards) post. Sets
        the macro scene for the period - grounded in the IHSG's own return
        and real macro news excerpts - rather than restating the leaderboard,
        which the image already shows in full.
        """
        news_excerpts = self._build_news_excerpts(news_articles, limit=6)
        system_prompt = self.prompts.system_prompt_companies_mover()
        user_prompt = self.prompts.user_prompt_companies_mover(index_return, date_range, leaders, laggards, news_excerpts)
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for companies-mover caption: {date_range}")
        return text

    def generate_becoming_insider_caption(
        self,
        event: dict,
        filing_excerpts: list[dict] | None = None,
        counterparty: dict | None = None,
        news_articles: list[dict] | None = None,
    ) -> str | None:
        """Caption for a holder crossing 5% ownership. `counterparty` is a
        best-effort match (see cli._find_counterparty_filing) for the other
        side of the same block trade, so the caption can name both parties
        when the data actually supports it instead of guessing.
        """
        news_excerpts = self._build_news_excerpts(news_articles)
        system_prompt = self.prompts.system_prompt_becoming_insider()
        user_prompt = self.prompts.user_prompt_becoming_insider(
            event, filing_excerpts, counterparty, news_excerpts
        )
        text = self._openai_complete(system_prompt, user_prompt)
        if text is None:
            print(f"OpenAI failed for becoming-insider caption: {event.get('base_symbol')}")
        return text
