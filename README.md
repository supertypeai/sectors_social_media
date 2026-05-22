# sectors_social_media

Image generator for Sectors social media content.

## Content pipeline

Filings:

1. `filings-daily`: daily post using the current insider-trading style template.
2. `filings-context`: one image per detected context cluster, grouped as cluster buy / cluster sell.
3. `filings-tags`: one image per important filing tag, currently including takeover and MESOP.

News:

1. `news-tier1`: one image per tier 1 news item.
2. `news-tier2`: one daily summary image for tier 2 news.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` with Supabase credentials:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
```

Generate directly from Supabase:

```bash
python -m image_generator.cli --mode filings-daily --output output
python -m image_generator.cli --mode filings-context --output output
python -m image_generator.cli --mode filings-tags --output output
python -m image_generator.cli --mode news-tier1 --output output
python -m image_generator.cli --mode news-tier2 --output output
```

Supabase fetch follows `data_gathering.ipynb`:

- Filings: `idx_filings.select("*").gte("timestamp", "2026-05-01")`
- News: `idx_news.select("*")`

Use `--filings-since YYYY-MM-DD` to move the filings lower bound.
News modes use the last 24 hours by default. Use `--hours`, `--limit`, or `--all-news` for backfills.
