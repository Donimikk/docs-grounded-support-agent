---
source: https://www.fyndit.app/docs/item-notifications
title: Item Notifications
---

# Item Notifications

Understand what happens when a monitored item matches your filters.

When the bot detects a new Vinted listing that passes all of your monitor's filters, it sends you a Discord notification, usually by DM. Some groups also use a feed channel. The notification is designed to give you everything you need to decide quickly without leaving Discord.

If you want to manage the monitor that produced the alert, open the Dashboard first and go to **Monitors**. The fallback command is /monitors.

## Embed Contents

Each notification embed includes the following information when available:

- **Item title** - The original listing title as posted by the seller, shown as the embed title. Clicking it opens the Vinted listing.
- **Price** - The item price, automatically converted to your session domain's currency if the seller is on a different domain.
- **Photos** - Up to 3 item photos are displayed directly in the embed. The first photo is the main image, with additional photos shown alongside.
- **Size** - The size selected by the seller, displayed with the size system label.
- **Brand** - The brand name if specified by the seller.
- **Condition** - The item condition (new with tags, new without tags, very good, good, satisfactory).
- **Color** - Color name when provided by the seller.
- **Seller information** - The seller's username, country flag (based on their ISO 2 country code), star rating (displayed as visual stars, where each star = 0.2 on the internal 0-1 scale), review count, and badges. Badges include: business account (briefcase icon), active lister, and speedy shipping.
- **Monitor name** - Which of your monitors matched this item, shown in the footer along with processing time in milliseconds.

## Action Buttons

Below the embed, you will find a row of persistent action buttons. They stay usable even after the bot restarts, so older notifications still work.

| Button | When you see it | What it does |
| --- | --- | --- |
| View | On every item notification. | Opens the Vinted listing in your browser. |
| Buy | On every buyable item. | Starts a purchase. If a queue already exists, you join it. If not, you create one and the bot starts buying. |
| Offer | On every buyable item that supports offers. | Lets you send a price offer to the seller. |
| Favorite / Unfavorite | On every item notification. | Adds or removes the item from your Vinted wishlist. The label changes after you click it. |
| Block / Unblock | On every notification that shows seller controls. | Hides future items from that seller. |
| Report Item | On queue notifications. | Marks the listing as suspicious and removes you from that queue. |
| Leave Queue | On queued autocop items. | Leaves the autocop queue without buying. |
| Decline | Only during 3DS. | Passes the turn to the next user in queue. |
| Watch Hidden | Only on hidden items. | Saves the hidden item so you can keep tracking it. |
| Restore | After a failed buy or queue outcome. | Returns the notification to the normal button set. |
| Retry | After a buy failure. | Lets you try again with a different session. |
| Mark as Kept | After a successful purchase. | Marks the item as kept so the bot stops reminding you about it. |
| Cancel Transaction | After a successful purchase. | Starts the cancellation flow if you need to cancel the order. |

## How the Bot Selects a Session for Actions

When you press Offer or Favorite, the bot picks the first compatible session it can use to reach the seller's country or domain. Selling sessions may still be used for favorites.

For automation (autocop/autooffer/autolike), rules can optionally be tied to a **session group**. When a rule has a session group selected, the bot only uses sessions from that group. If no session group is set, it falls back to any compatible session on your account.

## Notification Behavior

- Notifications can be delivered via Discord DMs or via a server feed channel (depending on how your group is configured). If you rely on DMs, make sure your privacy settings allow DMs from server members.
- Each notification is unique to your account. Multiple users monitoring the same criteria each receive independent notifications with their own buttons.
- Notification buttons are persistent across bot restarts. You can interact with notifications sent hours or even days ago.
- If autocop is enabled, the notification embed color changes to indicate the current state: normal match, queue, 3DS, success, or failure.

## Feed Colors

Feed colors are a way to keep notification streams separated. Think of each color as its own private inbox inside Discord.

Use different feed colors when you want to split alerts into tidy lanes, such as:

- one color for normal browsing
- one color for autocop or fast buys
- one color for hidden-item tracking
- one color for a second monitor setup you want to keep separate

If you only want one stream, you can leave everything on the same color and all alerts will continue to come through together.

## What The States Mean

- **Normal match** - The item matched one of your monitors and is ready for manual action.
- **Autocop active** - The item is already being handled by the autocop queue.
- **3DS pending** - Your bank still needs to approve the purchase.
- **Success** - The purchase went through and the bot will show the order details.
- **Failure** - The bot could not buy the item and will show the reason.

**Tip** Notification buttons are persistent across bot restarts. You can safely interact with notifications sent hours or even days ago.

## Hidden Items

Occasionally, Vinted flags certain items as hidden. Hidden items usually cannot be bought yet, so the notification may show fewer buttons. If your role allows it, you may see **Watch Hidden** so you can keep track of the listing until it becomes available again. For a full explanation, see the Hidden Item Watcher page in this manual.
