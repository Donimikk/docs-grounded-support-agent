---
id: dashboard-map
title: Map of the Dashboard — where things actually are
verified_by: the helper (by walking through the dashboard)
verified_on: 2026-09-10
---

# Everything is done through the Dashboard

The Dashboard lives in the channel #🖥️-use-vinted-bot-here and its messages are
private - only the person who opened it can see them.

**Never offer commands like `/monitors`.** They are written correctly, but they
are deliberately disabled so that there is one path and one tutorial instead of
two for the same thing. A customer who types such a command gets nothing and
comes back more confused. The documentation still lists them as a "fallback
command" - that is out of date.

This map was taken directly from the dashboard, so **where it differs from the
documentation, the map holds**.

## The seven buttons on the main screen

| Button | What is behind it |
| --- | --- |
| **Monitors** | groups, monitors, filters, rules, feed colours, webhook |
| **Sessions** | connected Vinted accounts, token, shipping, wardrobe |
| **Session Groups** | groups of accounts allowed to use rules |
| **My Info** | plan, limits, blocked sellers |
| **Preferences** | language, notification contents, cancellation reason |
| **Language** | a quick language change |
| **Quick Actions** | test an item, pause all rules |

## Monitors

**Your Groups** → *Select a group* or **Create Group**.

In the group menu: **Add Monitor**, **Edit Group** (the name), **Feed Colour**
(about 9 colours, each colour = a different bot delivering the group's
notifications), **Webhook** (a *Webhook URL* field, empty = off; what webhooks do
and that they are Pro only is described by `docs/webhooks` - the map adds WHERE
they are configured), **Group Filters** (whitelist/blacklist for the whole
group), **Group Seller Filters**, **Rules**, **Pause All**, **Delete Group**.

In a monitor's detail: **Edit Name**, **Edit Link** (a *Vinted URL* field - the
whole catalog link goes here), **Filters** (*Whitelist* and *Blacklist*, commas
and regex), **Seller Filters**, **Test Item** (paste a link to an item), **Test
Text** (paste a sample title/description), **Rules**, **Pause**, **Delete**.

**Seller Filters** contain: a minimum rating (*No minimum, ½, 1, 2, 3…*),
*Minimum Reviews*, *Exclude Pro*, *Show Hidden*, *Excluded Countries*.

## Rules — what is inside a rule

A rule is called **`item.matched`** and is described as "Configure actions,
schedule, and limits". The defaults after creating one:

| Item | Default |
| --- | --- |
| **Actions** | None configured |
| **Days** | Every day |
| **Hours** | All day |
| **Timezone** | UTC |
| **Uses** | Unlimited |
| **Expires** | Never |
| **Price Condition** | No condition |
| **Session Group** | None (all sessions) |

Controls: a *Select actions…* dropdown, **Monday–Sunday** day toggles, a session
group dropdown, and the buttons **Toggle**, **Hours**, **Limits**, **Price**,
**Delete**.

So a new rule **does nothing until an action is added to it** - *Actions* says
"None configured". This is the most common reason why "autocop is not working".

## Sessions — what is inside a session

A session card shows: the name, a coloured status ring, the domain (`vinted`),
the **type** (e.g. *Mixed*), the delivery method (e.g. *Home*), **Initialized:
Yes/No** and an ID.

Buttons: **Set Refresh Token**, **Shipping Config**, **Wardrobe**, a type toggle
(carrying the current type, e.g. *Mixed*), **Test OAuth**, **Pause**, **Delete
Session**, **Back**, and **Add Session**.

**The button is called "Set Refresh Token", not "Set Token".** The documentation
says "Set Token" and that is out of date. In a ticket about renewing a token the
customer was looking for exactly this button - the wrong name sends them hunting
for something that is not there.

The procedure for an inactive session: **Set Refresh Token** → **Test OAuth**.
Until that is done the card reports **Initialized: No** and the ring is red.

**Wardrobe is greyed out even for the `Mixed` type when the session is not
initialised.** The documentation only explains that it is disabled for the
*Buying* type - which is incomplete.

## Session Groups

A group card shows the number of members. Buttons: **Rename Group**, **Add
Session**, **Remove Session** (greyed out when the group is empty), **Delete
Group**, **Back**. You get here from Sessions through **Manage Session Groups**.

## My Info

Shows the User ID, name, language, roles and usage against the limits:
*Sessions*, *Groups*, *Monitors*, *Webhooks*, *Blocked Sellers*. The **Manage
Blocked** button opens a list with the option to unblock one or *Clear All*.

## Preferences

**Change Language**, **Embed Settings** (toggles for the fields in a
notification: *Price, Size, Brand, Condition, Color, Seller, Description,
Photos*) and **Cancel Reason** (the preset reason when cancelling an order).

## Language

*Select Language*: **English, Français, Deutsch, Español, Italiano.** The
documentation does not list the languages at all - this is the only list we have.

## Quick Actions

**Test Any Item** (an item link is tested against every monitor), **Pause All
Rules**, **Resume Paused Rules**.

## What is NOT in the dashboard

**Buy, Offer, Favorite, Block, Watch Hidden and Decline** are buttons on an item
notification, not dashboard panels. Do not send anyone into the dashboard for
them.

## Open contradictions

- The documentation claims Pro has **20 webhooks**; My Info on a Pro account
  shows **0/10**. We do not know which number holds - do not state either as
  certain.
- The documentation calls the seller filter **Exclude Business Accounts**, the
  interface says **Exclude Pro**.
- The documentation speaks of **Archive / Unarchive** on a monitor, the interface
  has **Pause**.

Related to [[bot-is-for-buying]]: Wardrobe and Promote are the same dead end -
they look like a route to selling and are not.
