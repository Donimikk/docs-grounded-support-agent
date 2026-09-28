---
source: https://www.fyndit.app/docs
title: Documentation — set up your Vinted bot
---

# Quick Start

Why Fyndit is useful, what each plan unlocks, and how to get set up fast.

Fyndit is a Discord bot that watches Vinted for you, filters the noise, and can act the moment a match appears. Start with the Dashboard for everyday use. If the Dashboard is unavailable, the slash commands below do the same job.

Open the Dashboard here: Open Dashboard

## Why Fyndit

Vinted moves fast, but the catalog can still feel slow and delayed when you rely on manual browsing. By the time you refresh, open the listing, and check the seller, the item may already be gone. Fyndit removes that lag by monitoring continuously, alerting you the moment it sees a match, and giving you the option to act instantly instead of starting from scratch every time.

That saves time in two ways:

- You stop checking the same catalog pages over and over.
- You react faster than manual browsing, so you miss fewer good items.

Fyndit also keeps your setup organized. Seller filters hide sellers you do not trust or do not want to see, and feed colors split alerts into separate private streams so your buying, watching, and testing traffic stay tidy instead of mixing together.

## Core Features

| Feature | What it does | Why it matters |
| --- | --- | --- |
| No-delay monitoring | Watches continuously and alerts you as soon as a match appears. | You get the item before a slower manual refresh cycle has a chance to bury it. |
| Autocop | Buys automatically when a match hits your rule. | Best for items that sell fast and need instant action. |
| Autooffer | Sends an offer automatically or from the item flow. | Helps you move first without manually opening every listing. |
| Autolike | Favourites items automatically or from the item flow. | Lets you save interesting items quickly without extra taps. |
| Multicop | Lets multiple accounts fire on the same item at once to improve your chance of buying. | Useful when you want more than one authenticated account to try the purchase together instead of waiting on just one. |

**Tip** Fyndit is built for speed first: the goal is to spot items early, act quickly, and save you the time you would normally spend refreshing Vinted by hand.

## What Each Plan Gives You

| Tier | Best for | What you should expect |
| --- | --- | --- |
| Free | Trying the interface | A limited setup so you can explore the dashboard and see how alerts look, but not a full buying workflow. |
| Plus | Most buyers | One complete personal setup: a real Vinted account, monitors, no-delay alerts, and the core automation features you will actually use day to day. |
| Pro | Heavy users | Everything in Plus with much higher limits, more sessions, more monitors, webhooks, and priority autocop handling. |

**Tip** For the exact limits, see Roles, Permissions & Limits or open the matching docs page in the sidebar.

In plain English: Free is for trying the app, Plus is the normal full setup for one buyer, and Pro is for power users who need more accounts, more monitors, and webhooks.

## Prerequisites

Before you begin, make sure you have the following ready:

- A Discord account that has joined the Fyndit server. You need to be a member of the server to use the bot.
- An active Vinted account on any supported domain.
- Your Vinted refresh token, which allows the bot to authenticate as your account. Instructions on how to obtain it are pinned in the server.
- Discord DMs enabled (recommended). Most users receive notifications as direct messages. Some setups may also post matches in a server feed channel.

## Step-by-Step Setup

1. Buy your plan in Whop and connect Discord so the correct role is assigned. If you need the links, open Subscription & Billing first.
2. Open the Dashboard and use **Sessions** to create your first session. The fallback command is /sessions.
3. Enter a friendly name for the session, then choose the correct Vinted domain for that account.
4. Click **Set Token** and paste your Vinted refresh token. Then click **Test OAuth** to confirm the account is connected.
5. Open the Dashboard and use **Monitors** to create your first group. The fallback command is /monitors.
6. Open the group, click **+ Add Monitor**, paste a Vinted catalog URL, and save. The bot starts scanning immediately.
7. If you want the bot to speak a different language, open the Dashboard and use **Preferences**. The fallback command is /preferences.

**Tip** You can also do most of this from the Dashboard: Open Dashboard

## How Notifications Work

Once a monitor is active, the bot continuously checks Vinted for new listings that match your filters. When a match is found, you receive a Discord notification, usually a DM. Some setups also post in a server feed channel. The notification contains the item details plus action buttons like View, Buy, Offer, Favorite, and Block.

If you are not seeing notifications:

- Make sure the monitor is active, not archived.
- Make sure your session is authenticated.
- Make sure Discord DMs are allowed from the server.
- Use the item test tools in the monitor panel if the filters seem too strict.

## Supported Vinted Domains

Each session connects to a specific Vinted domain. The domain determines the marketplace, currency, available shipping carriers, and catalog structure. You can create sessions on multiple domains simultaneously to monitor different marketplaces.

**Tip** You can change your language at any time in /preferences. This only affects how the bot speaks to you on Discord. It does not change which Vinted marketplace your sessions connect to.

## Common Setup Issues

- **Token rejected when setting up a session** - The refresh token may have expired or been copied incorrectly. Make sure you copy the full token string without any extra spaces. Obtain a fresh token and try again.
- **No notifications received** - Check that your Discord DM privacy settings allow messages from server members. Also verify your monitor is active (not archived) and your session is authenticated.
- **"Invalid domain" error when creating a session** - The domain code must be one of the supported codes listed above (lowercase, no dots). For example, use `fr`, not `vinted.fr` or `FR`.
