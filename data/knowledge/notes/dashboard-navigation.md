---
id: dashboard-navigation
title: Dashboard — click paths, exact field names, and what each screen offers
verified_by: the helper
verified_on: 2026-08-16
---

# Where things are in the Dashboard

Mapped by walking the Dashboard in `#🖥️-use-vinted-bot-here` and reading the
screens directly. The documentation lists the seven top-level buttons; this is
the level below that — **what you click to reach a setting, what the field is
called, and what the options actually are.**

Use it when a customer asks "where do I find X". Give them the click path.

All Dashboard messages are private — only the person who opened it sees them.

## Monitors — three levels deep

```
Monitors
  └─ Your Groups            (pick a group, or Create Group)
       └─ Group menu        (group-wide settings + list of monitors)
            └─ Monitor      (settings for one search)
```

**Several settings exist at both levels** and people set them in the wrong
place:

| Setting | Group level | Monitor level |
| --- | --- | --- |
| Filters (whitelist / blacklist) | Group Filters | Filters |
| Seller filters | Group Seller Filters | Seller Filters |
| Rules | Rules | Rules |
| Webhook | Webhook | — group only |
| Feed colour | Feed Colour | — group only |

A whitelist set on the group applies to every monitor inside it.

### Group menu buttons

`Select a monitor…`, `➕ Add Monitor`, `🖌️ Edit Group` (Group Name),
`🎨 Feed Colour`, `🪝 Webhook` (Webhook URL, empty = off), `🔍 Group Filters`,
`⭐ Group Seller Filters`, `⚙️ Rules`, `⏸️ Pause All`, `🗑️ Delete Group`.

### Monitor buttons

`✏️ Edit Name`, `🔗 Edit Link` (field: **Vinted URL**), `🔍 Filters`,
`⭐ Seller Filters`, `📝 Test Item`, `📝 Test Text`, `⚙️ Rules`, `⏸️ Pause`,
`🗑️ Delete`.

The monitor screen also shows category, region, status, match count, speed and
last match — useful when a customer says "it isn't finding anything", because
the match count and last match are right there.

## Feed Colour

Found under **Monitors → group menu → 🎨 Feed Colour**. Nine colours.
The screen states it plainly:

> Each colour corresponds to a different bot. Notifications for this group will
> be sent through the bot matching the selected colour.

So the colour is not decoration — it decides **which bot delivers that group's
notifications**. This is why customers sometimes see alerts arrive from what
looks like a different account.

## Rules — the part the documentation does not list

A rule screen looks like `item.matched (Active)` and configures actions,
schedule and limits.

**Available actions** (multi-select dropdown):

`🛒 Auto-Buy`, `🔔 Ping on Match`, `❤️ Auto-Like`, `💰 Auto-Offer`,
`🛍️ Manual Buy`, `💬 Manual Offer`, `❤️ Manual Favourite`

**Fields shown on the rule:**

- **Days** — per-weekday toggles, default *Every day*
- **Hours** — default *All day*; timezone shown separately, default **UTC**
- **Uses** — default *Unlimited*
- **Expires** — default *Never*
- **Price Condition** — default *No condition*
- **Session Group** — default *None (all sessions)*

Buttons: `Toggle`, `Hours`, `Limits`, `Price`, `Delete`, `Back`.

Two things worth telling customers: the timezone defaults to **UTC**, not their
local time, and a rule with no session group runs against **all** sessions.

## Sessions

Empty state says "You don't have any sessions yet" with `➕ Create Session` and
`📁 Manage Session Groups`.

Once a session exists it appears as `name — vinted` with a status dot, and a
`Select a session…` dropdown.

**Session detail** shows name, platform, mode (e.g. *Mixed*), delivery mode
(e.g. *Home*), `Initialized: Yes/No`, and the session ID.

Buttons: `🔑 Set Refresh Token`, `📦 Shipping Config`, `👕 Wardrobe`
(greyed out until initialized), mode button (`Mixed`), `🔄 Test OAuth`,
`⏸️ Pause`, `🗑️ Delete Session`, `🔙 Back`, `➕ Add Session`.

A **red dot with `Initialized: No`** means the token has not been set yet — that
is the normal state right after creating a session, not a fault.

## Shipping Config (inside a session)

Three dropdowns and three buttons:

- **Home Delivery** — delivery mode
- **Flexible** — strictness
- **Favorite pickup** — pickup strategy, shown with the radius (e.g. *5 km*)
- `📍 Set Location`, `⭐ Set Favorite Pickup`, `📏 Pickup Radius`, `🔙 Back`

Until a location is set the screen says *"Set a location to enable pickup point
selection"* — so **location comes first**; the favourite pickup cannot be chosen
before it.

## Seller Filters — the exact fields

- minimum rating dropdown — `No minimum`, `½`, `1`, `2`, `3`, …
- **Minimum Reviews**
- **Exclude Pro** — leave out professional sellers
- **Show Hidden**
- **Excluded Countries** — dropdown

Note the wording: it is **Excluded** Countries, a blocklist. Customers often
expect to pick the countries they *want*.

## Testing a filter — three different buttons

- **Test Item** (on a monitor) — paste a Vinted item URL, see if it passes
  *that monitor's* filters
- **Test Text** (on a monitor) — paste sample title/description text instead of
  a URL; useful when they only want to check the wording rules
- **Test Any Item** (Quick Actions) — checks an item against **all** monitors

When someone asks "will my filter catch this", Test Text is usually what they
want, and it is the one people do not know exists.

## Preferences

- **Change Language**
- **Embed Settings** — toggles for which fields appear in an item notification:
  Price, Size, Brand, Condition, Color, Seller, Description, Photos
- **Cancel Reason** — default reason used when cancelling a purchase; empty
  means the standard reason

## Language

Dashboard language picker offers English, Français, Deutsch, Español, Italiano.

## My Info

Shows User ID, Name, Language, Roles, and usage counters: Sessions, Groups,
Monitors, Webhooks, Blocked Sellers.

`🚫 Manage Blocked` opens the blocked-seller list with `Select to unblock…`
and `Clear All`.

Point customers here when they ask "how many monitors do I have left" — the
counters show usage against their plan limits.

## Session Groups

Reusable sets of Vinted accounts that automation rules draw from. Empty until
sessions exist, which is why a new customer sees nothing here.
