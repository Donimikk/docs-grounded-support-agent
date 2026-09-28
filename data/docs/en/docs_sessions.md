---
source: https://www.fyndit.app/docs/sessions
title: Sessions
---

# Sessions

Link your Vinted accounts and configure shipping preferences.

A session represents a linked Vinted account that the bot uses to interact with Vinted on your behalf. Every action the bot performs (buying items, making offers, favoriting listings, browsing wardrobes, promoting items) requires a valid session. Use the Dashboard first. If you need a direct path, the fallback command is /sessions.

Open the Dashboard here: Open Dashboard

## Why Sessions Exist

The bot cannot interact with Vinted without being authenticated as a real Vinted user. A session holds the authentication credentials (refresh token) for one of your Vinted accounts, along with your shipping preferences for that account. You can create multiple sessions and (optionally) organize them into **session groups** to control which accounts are used for automation.

## Creating a Session

1. Open the Dashboard and choose **Sessions** or use /sessions.
2. Click **+ Create** to add a new session.
3. Give the session a name you will recognize later.
4. Choose the correct Vinted domain for that account.
5. Click **Set Token** and paste the refresh token from Vinted.
6. Click **Test OAuth** to make sure the session is ready. If it works, the session turns active and shows the Vinted username.

**Tip** Prefer using the Dashboard for day-to-day session management: Open Dashboard

## Status Indicators

Sessions use colored indicators to show their current state at a glance:

- **Green circle** - The session is active and authenticated. The bot can use it for all operations.
- **Red circle** - The session has been created but is not yet authenticated (no token set or token invalid). Set or refresh the token to activate it.
- **Pause icon** - The session is archived. It retains all configuration but the bot will not use it for any operations.

## Account Types

Each session has a type that controls what the bot is allowed to do with it. This lets you separate buying and selling activities across different accounts:

- **Mixed** - The default type. The session can be used for both buying features (purchases, offers, favorites) and selling features (wardrobe browsing, item promotion). Suitable if you use a single Vinted account for everything.
- **Buying** - Restricted to buying operations only. The bot will use this session for purchases, offers, and favoriting items, but will never use it for wardrobe browsing or item promotion. The Wardrobe button is disabled for this type.
- **Selling** - Restricted to selling operations only. The bot will use this session for wardrobe browsing and item promotion, but will not use it for buying actions (buy, offer, favorite, autocop).

You can cycle through account types by clicking the type button on the session panel. Each click rotates: Mixed, then Buying, then Selling, then back to Mixed.

## Shipping Configuration

Before the bot can buy items for you, you need to configure your shipping preferences. Click **Shipping Config** on a session to open the shipping settings panel.

## Delivery Mode

- **Pickup Point** - The item is delivered to a nearby collection point (post office, locker, relay point). You pick it up at your convenience. This is the default mode and is available in most European countries.
- **Home Delivery** - The item is delivered directly to your home address. Availability depends on the seller's shipping options and the carriers in your region.

## Shipping Strictness

- **Flexible** (default) - The bot accepts any carrier the seller offers. This maximizes your chances of a successful purchase because it will not fail due to carrier incompatibility. Recommended for autocop users.
- **Strict** - The bot only accepts your preferred carrier. If the seller does not offer that specific carrier, the purchase will fail. Use this only if you have a strong preference for a particular delivery service.

## Setting Your Location

Your location is required for finding nearby pickup points and for home delivery. Click **Set Location** and enter your full address. The bot shows the result back to you so you can confirm it or try again if it is not right. A more specific address gives a better result.

## Favorite Pickup Point

After setting your location, you can search for nearby pickup points and save one as your favorite. Click **Set Favorite Pickup** then **Search Nearby**. The bot shows nearby pickup points so you can choose one and save it as your default. During autocop purchases, the bot can use this point automatically, which makes checkout faster.

**Tip** Setting a favorite pickup point dramatically speeds up the checkout process during autocop, since the bot does not need to search for nearby points at purchase time. This can make the difference between getting an item and losing it.

## Video Guide

Choose pickup points

## Pickup Strategy and Radius

If you use pickup delivery, you can choose how the bot selects a pickup point during checkout:

- **Favorite** - Always use your saved favorite pickup point.
- **Favorite → Cheapest fallback** - Use favorite when possible, otherwise choose a cheap available point.
- **Closest & Cheapest** - Choose a nearby point based on distance and price.

The **Pickup Radius** controls how far the bot is allowed to search (in km) when it needs to pick a point automatically.

## Archive and Delete

- **Archive** - Temporarily disables a session without losing any configuration. Archived sessions retain all settings but the bot will not use them. You can unarchive at any time.
- **Delete** - Permanently removes a session and all its data. This is irreversible.

**Warning** Deleting a session is permanent. All pool assignments, shipping configuration, and token data will be lost forever. Archive the session instead if you might need it again later.

## Troubleshooting

- **Test OAuth fails** - Your refresh token has likely expired. Obtain a fresh token from Vinted and set it again.
- **Can't connect your Vinted account** - Log out of Vinted, log back in, copy the full `refresh_token_web` value again, and paste it back into the token field. Then run **Test OAuth** one more time.
- **Session stays red after setting token** - Make sure you pasted the complete token without trailing spaces or line breaks.
- **Cannot create more sessions** - You have reached your plan's session limit. Check with /my_info.
- **Wardrobe button is disabled** - Your session type is set to "Buying". Change it to "Mixed" or "Selling".
