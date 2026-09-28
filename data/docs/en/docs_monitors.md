---
source: https://www.fyndit.app/docs/monitors
title: Monitors
---

# Monitors

Create and configure catalog monitors with advanced filtering.

Monitors are the core of Fyndit. A monitor watches a specific Vinted catalog page and notifies you whenever a new listing appears that matches your criteria. Use the Dashboard first to open this area. The fallback command is /monitors.

Open the Dashboard here: Open Dashboard

Monitors are organized into groups, which let you share configuration across related monitors. You can have multiple groups, each with multiple monitors, covering different categories, brands, or price ranges.

Seller filters sit alongside your normal text and URL filters. Use them when you only want to see sellers you trust, when you want to skip business accounts, or when you want to keep risky sellers out of your alerts before they ever reach your inbox.

## Monitor Groups

Groups are containers that hold one or more monitors. Every monitor must belong to a group. Groups serve two purposes: organization and shared settings. You can name and color-code each group, making it easy to distinguish between different monitoring strategies.

1. Open the Dashboard and choose **Monitors**, or use /monitors.
2. Click **Create Group** and enter a name for the group.

Groups can also store group-level filters and rules. These apply to every monitor in the group, so you can set a baseline once and only fine-tune specific monitors when needed.

**Tip** You can also manage groups and monitors from the Dashboard: Open Dashboard

## Adding a Monitor

To add a monitor, you need a Vinted catalog URL. Go to Vinted, apply all the filters you want, and copy the resulting URL from your browser's address bar. The bot reads that URL and turns it into a monitor.

1. Open a group and click **Add Monitor**.
2. Paste the full Vinted catalog URL in the input field.
3. Optionally give the monitor a custom name.
4. Save it and the bot begins monitoring immediately.

The following URL-based filters are automatically extracted and shown in the monitor details:

- **Catalog** - The category path you selected.
- **Brand** - The brand filter from Vinted.
- **Size** - The size or sizes you selected.
- **Price range** - Minimum and maximum price.
- **Condition** - Item condition.
- **Color** - Color filter.
- **Material** - Material filter.
- **Pattern** - Pattern filter.
- **Search text** - The keyword search from the URL.
- **Region/domain** - The marketplace this monitor uses.

**Tip** Apply as many filters as possible directly on Vinted before copying the URL. The more specific the URL, the fewer irrelevant matches you will receive and the faster the bot can process results.

## Video Guide

Create monitors

## Text Filters (Whitelist and Blacklist)

Beyond the URL-based filters, you can define text-based filters that match the item title and description. Open a monitor, click **Filters**, then add your patterns as a comma-separated list.

See **Filters & Regex** for examples and common patterns.

## Seller Filters

Seller filters help you decide which sellers are worth seeing. Click **Seller** on a monitor to configure:

- **Minimum Rating** - Only show sellers at or above the chosen star rating.
- **Minimum Reviews** - Only show sellers with at least this many reviews.
- **Exclude Business Accounts** - Hide professional or business sellers.
- **Show Hidden Items** - Include hidden listings if your role allows them.

What this means in practice:

- Use a higher minimum rating when you want safer, cleaner alerts.
- Use a higher review count when you want more established sellers only.
- Turn off business accounts if you only want private sellers.
- Enable hidden items only if you want to keep track of listings that are not fully visible yet.

## Test Item

The Test Item feature lets you verify whether a specific Vinted listing would pass or fail your monitor's filters. Click **Test Item**, paste a Vinted item URL, and the bot shows whether the item would match.

Use **Test Text** when you only want to check the text filters. That is useful if you already know the item URL is correct and you just want to see why the wording passed or failed.

If the item would be rejected, the bot shows a human-readable reason explaining what failed. This is the fastest way to debug a monitor that feels too strict or too loose.

## Monitor Management

Each monitor can be renamed, relinked, filtered, tested, paused, resumed, or deleted.

- **Edit Name** - Change the monitor's display name.
- **Edit Link** - Replace the Vinted catalog URL.
- **Filters** - Edit whitelist and blacklist text filters.
- **Seller** - Edit seller rating, review count, business-account, hidden-item, and country rules.
- **Test Item** - Check one Vinted item against the full monitor.
- **Test Text** - Check a piece of text against only the text filters.
- **Rules** - Add or edit the actions that run when the monitor matches.
- **Archive / Unarchive** - Pause or resume one monitor.
- **Pause All / Unarchive All** - Pause or resume every monitor in the group.
- **Delete** - Remove the monitor permanently.

## Troubleshooting

- **Not getting any notifications** - Check that the monitor is active (green play icon, not paused). Verify your session is authenticated. Use Test Item to check if your filters are too strict.
- **Too many notifications** - Your filters are too broad. Apply more specific URL filters on Vinted or add blacklist patterns to exclude unwanted items.
- **Test Item says "Wrong category"** - The item's category does not match the catalog IDs in your monitor URL. Make sure you copied the URL from the correct Vinted category page.
- **"No whitelist match"** - The item text does not match your whitelist. If you used regex, make sure it’s wrapped like `/.../` (otherwise it’s treated as a literal keyword).
- **You don't have access to that feature / cannot create more monitors** - Your plan has reached its monitor limit, or the feature is locked on your current tier. Upgrade if you want more monitors or extra features. If you have not claimed a role yet, you can still start on Free and get 1 free monitor.
