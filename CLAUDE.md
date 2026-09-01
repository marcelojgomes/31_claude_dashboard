# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

The dashboard is implemented as a single-page **Streamlit** app (`app.py`), styled dark to match the visual language of `design-system/`. There is no separate build step, linter, or test suite configured.

Run it with:

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens at `http://localhost:8501`. `.streamlit/config.toml` sets the dark theme (background/accent colors matching the dataviz palette below); no other config is needed.

The repo has two source inputs the app is built from:

- `dataset/` — the actual data the dashboard visualizes (e-commerce data).
- `design-system/` — a scraped static HTML export used purely as **visual/style reference**, not code that was reused directly.

## dataset/

Four CSVs describing an e-commerce business:

- `customers.csv` (8000 rows) — one row per customer: demographics (`country`, `age`, `gender`), `membership_tier`, `registration_date`, aggregate behavior (`total_orders`, `total_spend_usd`, `avg_order_value_usd`, `days_since_last_purchase`), preferences (`preferred_category`, `preferred_device`, `preferred_payment_method`), `acquisition_channel`, review/return stats, `newsletter_subscribed`, and `churned` (0/1).
- `orders.csv` (25000 rows) — one row per order line: `order_id`, `customer_id`, date/time fields (`order_date`, `year`, `month`, `quarter`, `day_of_week`), product info (`product_name`, `category`, `unit_price_usd`, `quantity`), pricing breakdown (`subtotal_usd`, `discount_pct`, `discount_amount_usd`, `shipping_fee_usd`, `tax_pct`, `tax_amount_usd`, `total_amount_usd`), `payment_method`, `device_used`, delivery info, `order_status`, `returned`, `customer_rating`, and session/funnel fields (`session_duration_minutes`, `pages_viewed_before_purchase`, `is_repeat_customer`).
- `monthly_revenue.csv` (75 rows) — pre-aggregated monthly rollup: `year`, `month`, `quarter`, `orders`, `revenue_usd`, `avg_order_value`, `avg_discount_pct`, `return_rate`, `unique_customers`, `new_customers`. Use this directly for revenue-over-time charts instead of re-aggregating `orders.csv` when a monthly view is enough.
- `product_summary.csv` (140 rows) — pre-aggregated per-product rollup: `category`, `product_name`, `total_orders`, `total_revenue_usd`, `avg_price`, `avg_rating`, `return_rate`, `avg_discount_pct`, `avg_delivery_days`. Use this directly for product/category leaderboards instead of re-aggregating `orders.csv`.

`customer_id` in `customers.csv` and `orders.csv` is the join key. `category`/`product_name` join `product_summary.csv` to `orders.csv`.

## design-system/

`design-system/index.html` (plus its `assets/`) is a static export of an **unrelated** demo UI (a "garden/irrigation control" dashboard, not an e-commerce one). Its actual content and copy are irrelevant — treat it strictly as a source of visual style to mimic when building the real dashboard:

- Tailwind utility classes for a dark theme (`bg-neutral-950`, glassy cards with `bg-white/15` + `border-white/30`, rounded-3xl cards, `shadow-lg shadow-*-900/40`), a 12-column responsive grid (`grid-cols-1 md:grid-cols-8 lg:grid-cols-12`) of stat/rule cards.
- Icons via the Iconify "solar" set (`iconify--solar`, e.g. `data-icon="solar:temperature-bold-duotone"`) and a Lucide script include.
- A large set of self-hosted Google Fonts (Geist, Roboto, Montserrat, Poppins, Playfair Display, Instrument Serif, Merriweather, Bricolage Grotesque, Plus Jakarta Sans, Manrope, Space Grotesk, Work Sans, PT Serif, Geist Mono, Space Mono, Quicksand, Nunito) loaded as `.font-*` utility classes — treat these as an available palette of type choices, not a requirement to use all of them.
- A decorative animated background (`UnicornStudio` script) — do not carry this over unless explicitly asked; it's unrelated to dashboard functionality.

Do not copy this file's content, component structure, or business domain into the new dashboard — only its visual language (color/spacing/card/typography conventions).

## app.py structure

- `load_data()` reads `orders.csv` / `customers.csv` directly (not the pre-aggregated `monthly_revenue.csv` / `product_summary.csv`) and is `@st.cache_data`-cached, so every chart recomputes from the same filtered `orders` frame and stays consistent with the sidebar filters (year range, category, device, order status). The customer-segment section at the bottom intentionally uses the full `customers` table, unaffected by those filters — it's labeled as such in the UI.
- Chart styling follows the project's `dataviz` skill: a validated dark-mode palette (hex constants near the top of the file — `BLUE`, `ORANGE`, `AQUA`, etc.), fixed name→color maps for entities with few categories (`TIER_COLORS`, `CHANNEL_COLORS`, `DEVICE_COLORS`) so color always follows identity rather than sort order, single-hue bars for plain magnitude rankings (no per-category color needed there), and no dual-axis charts — revenue and order-volume trends are two separate stacked charts rather than one chart with two y-scales. `style_fig()` centralizes the dark chart chrome (surface/gridline/ink colors) applied to every Plotly figure.
- When adding a new chart, follow the same skill (`references/palette.md` inside it has the full hex table) rather than picking colors ad hoc.
