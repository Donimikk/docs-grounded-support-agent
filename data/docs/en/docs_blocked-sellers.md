---
source: https://www.fyndit.app/docs/blocked-sellers
title: Blocked Sellers
---

# Blocked Sellers

Manage a personal list of sellers you do not want to see items from.

The Blocked Sellers feature lets you maintain a personal exclusion list of Vinted sellers. Use the Dashboard first, or open /my_info if you prefer the command path. When you block a seller, all of their future items are silently filtered out across every one of your monitors.

This is useful for sellers you do not want to see again, sellers with misleading listings, or accounts you simply want to ignore.

## Blocking a Seller

There are two ways to block a seller:

- **From a notification** - Click the **Block** button on any item notification embed. The seller of that item is immediately added to your blocked list. You will never see their items in any monitor again. If the seller is already blocked, the bot tells you so.
- **From account management** - Run /my_info and click **Manage Blocked** to open the blocked sellers management panel. From here you can view your full blocked list, unblock individual sellers, or clear the entire list.

**Tip** You can also manage your blocked sellers from the Dashboard: Open Dashboard

## How Blocking Works Internally

Blocked sellers are checked at the **earliest stage** of the filtering pipeline. When the bot receives a batch of new items from Vinted, it checks each item's seller against your blocked list before applying any other filters (text filters, seller rating filters, URL-based filters). This means blocked seller checks are extremely fast and do not waste processing time on items you will never see.

The blocked sellers list is cached in memory and refreshed periodically for performance. When you block or unblock a seller, the cache is updated immediately so the change takes effect right away.

## Managing Your List

The management panel (accessible via /my_info then **Manage Blocked**) displays all your blocked sellers with their Vinted usernames and seller IDs. The list is paginated if you have many blocked sellers (10 per page). You can:

- **Unblock specific sellers** - Select one or more sellers from the multi-select dropdown and they will be removed from your blocked list.
- **Clear all** - Click the trash button to remove every seller from your blocked list at once. The bot asks for confirmation before clearing since this action affects all your monitors.
- **Navigate pages** - Use the Previous and Next buttons if your list spans multiple pages.

Your total blocked seller count is also shown in the /my_info panel alongside your session, group, and monitor counts.

## What To Expect

- **Block** removes future items only. It does not hide items you already received.
- **Unblock** lets that seller show up again.
- **Clear all** removes the entire list, so use it only if you really want a fresh start.
