---
source: https://www.fyndit.app/docs/favorites
title: Favorites
---

# Favorites

Like and unlike items on Vinted from your notifications.

The Favorite feature lets you like or unlike items on Vinted directly from your Discord notification. Open the item from the Dashboard first, or use the notification in DM. The fallback command is /monitors.

Favoriting an item adds it to your Vinted wishlist and signals interest to the seller, which can sometimes prompt them to send you a discount offer.

## How It Works

Click the **Favorite** button on any item notification to toggle the like status. If the item is not currently in your favorites, the bot adds it. If it is already favorited, the bot removes it. The button visually updates after each toggle.

## Session Selection

To favorite or unfavorite, the bot uses the first compatible session it can use to reach the seller's country or domain. Selling-type sessions may still be used.

## Automatic Favorites via Rules

You can automate favoriting through the Rules system. Create a rule with the **Autolike** action enabled, and the bot will automatically like every item that matches the monitor. This is useful for:

- Building a wishlist of specific item types automatically.
- Signaling interest to sellers who might lower their prices in response to favorites.
- Tracking items you are interested in without manually clicking each notification.

See the Rules section for full configuration options including scheduling and limits.

## What To Expect

- If the button says **Favorite**, the item is not liked yet.
- If the button says **Unfavorite**, the item is already liked.
- If the action fails, it usually means you do not have a usable session for that seller's region.
