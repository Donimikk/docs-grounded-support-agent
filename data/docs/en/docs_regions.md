---
source: https://www.fyndit.app/docs/regions
title: Regions & Cross-Border Visibility
---

# Regions & Cross-Border Visibility

Understand which Vinted domains can see items from each seller country.

Vinted is not a single unified marketplace. It operates as a network of regional domains, and items listed in one country are only visible on certain other domains. This cross-border visibility system determines which sessions can see, buy, offer on, and favorite items from sellers in different countries. Understanding regions is essential for setting up sessions and monitors correctly. If you are coming from the Dashboard, use **Sessions** or **Monitors** to apply this information.

## How It Works

Each Vinted seller is located in a specific country. Their items are visible on their own domain plus a defined set of neighboring domains. For example, a seller in France (`fr`) has their items visible on `at`, `be`, `de`, `ie`, `it`, `lu`, `nl`, `pt`, and `es`. A buyer with a session on `vinted.de` can see and purchase French items, but a buyer on `vinted.pl` cannot.

This means your session domain directly determines which sellers you can interact with. If you want to buy from sellers across all of Europe, you need sessions on multiple domains.

## Visibility Table

The first column is the seller's country. The remaining columns are the domains where their items are visible (in addition to their own domain).

| Seller Country | Visible On |
| --- | --- |
| Austria (at) | fr, it |
| Belgium (be) | fr, de, it, lu, nl, pt, es |
| Croatia (hr) | pl |
| Czech Republic (cz) | pl, sk |
| Denmark (dk) | fi, pl, se |
| Estonia (ee) | lv, lt, pl |
| Finland (fi) | dk, lt, pl, se |
| France (fr) | at, be, de, ie, it, lu, nl, pt, es |
| Germany (de) | be, fr, it, nl |
| Greece (gr) | hu, ro |
| Hungary (hu) | gr, pl, ro |
| Ireland (ie) | fr |
| Italy (it) | at, be, fr, de, lu, nl, pt, es |
| Latvia (lv) | ee, lt, pl |
| Lithuania (lt) | fi, pl, ee, lv |
| Luxembourg (lu) | be, fr, it, nl, pt, es |
| Netherlands (nl) | be, fr, de, it, lu, pt, es |
| Poland (pl) | hr, cz, dk, ee, fi, hu, lv, lt, ro, sk, si, se |
| Portugal (pt) | be, fr, it, lu, nl, es |
| Romania (ro) | gr, hu, pl |
| Slovakia (sk) | cz, pl |
| Slovenia (si) | pl |
| Spain (es) | be, fr, it, lu, nl, pt |
| Sweden (se) | dk, fi, pl |
| United Kingdom (uk) | us |
| United States (us) | uk |

## Key Observations

- **Western Europe cluster** — France, Italy, Belgium, Netherlands, Luxembourg, Portugal, Spain, and Germany form the most interconnected group. A session on `fr` or `it` covers the widest range of Western European sellers.
- **Nordic/Baltic cluster** — Denmark, Finland, Sweden, Estonia, Latvia, and Lithuania are linked primarily through Poland and each other.
- **Central/Eastern cluster** — Poland is the hub connecting Czech Republic, Slovakia, Hungary, Romania, Croatia, Slovenia, and the Baltic/Nordic countries. A `pl` session covers the most Eastern European sellers.
- **UK and US** — These two are isolated from mainland Europe and only see each other.
- **Ireland** — Only visible on France. Irish sellers have the most limited cross-border reach in Europe.

## Practical Implications

- **Monitor coverage** — When creating monitors, your session domain must be able to see the seller countries you care about. A monitor on a `fr` session will never surface items from Polish, Swedish, or Romanian sellers.
- **Session pool strategy** — To maximize coverage, use a pool combining a Western European domain (e.g. `fr` or `it`) with `pl` for Eastern Europe. This covers nearly all 26 countries except UK/US.
- **Buying and offers** — The Buy, Offer, and Favorite actions require a session on a domain that can see the seller's country. If no compatible session exists in your pool, the action fails with a "no compatible session" error.
- **Cross-domain purchases** — A buyer on `vinted.fr` can buy from a German seller because `de` items are visible on `fr`. The price is automatically converted to the buyer's domain currency.

## Session Domain Recommendations

| Goal | Recommended Domains |
| --- | --- |
| Western Europe only | fr or it |
| Eastern Europe only | pl |
| Full Europe coverage | fr + pl |
| UK/US | uk or us |
| Maximum reach | fr + pl + uk |
