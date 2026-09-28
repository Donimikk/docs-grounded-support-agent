---
source: https://www.fyndit.app/docs/filters
title: Filters & Regex
---

# Filters & Regex

Use whitelist/blacklist filters to include or exclude items by text.

Filters let you control what you get notified about beyond Vinted's built-in URL filters. They match against the **item title + description** combined. Open the monitor panel from the Dashboard first, then use the filter button. The fallback command is /monitors.

## Where to Set Filters

1. Run /monitors.
2. Open a group, then select a monitor.
3. Click **Filters** to edit whitelist/blacklist.

Some filters can also be set at the **group** level (applies to every monitor in the group).

**Tip** You can also adjust filters from the Dashboard: Open Dashboard

## Whitelist vs. Blacklist

- **Whitelist** - A comma-separated list of patterns. The item must match **at least one** pattern to pass. If whitelist is empty, everything passes this step.
- **Blacklist** - A comma-separated list of patterns. If the item matches **any** pattern, it is rejected.

## Regex Basics (Quick)

- Patterns are **case-insensitive**.
- Separate multiple patterns with **commas**.
- By default, each entry is treated as a **keyword** (literal text).
- Keyword matching is “whole word/phrase” style (so `max` won’t match `maxx`).
- To use **regex**, wrap it with `/` at the start and end: `/your_regex_here/`.

## Useful Patterns

- `nike air max` - Keyword match (literal text).
- `/nike|adidas/` - Regex: matches either “nike” or “adidas”.
- `/^jordan/` - Regex: matches text that starts with “jordan”.
- `/\bvintage\b/` - Regex: matches the whole word “vintage” (not “vintagestyle”).
- `/replica|fake|custom/` - Regex: common blacklist pattern to avoid fakes.
- `/taille\s*(42|43|44)/` - Regex: matches “taille 42/43/44” in French descriptions.

## Common Mistakes

- **Writing regex without `/.../`** - `nike|adidas` is treated as a literal keyword, not regex. Use `/nike|adidas/`.
- **Using spaces instead of commas** - Use commas to separate patterns.
- **Using commas inside a regex** - The input is split by commas, so keep regex entries comma-free.
- **Over-filtering** - If you get zero matches, temporarily clear whitelist and re-add patterns one by one.

## Debugging with Test Tools

Use **Test Text** to quickly check if a piece of text would pass your filters, and **Test Item** to see exactly which filter stage rejected a real Vinted item.
