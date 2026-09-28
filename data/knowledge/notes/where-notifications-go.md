---
id: where-notifications-go
title: A monitor is not used in the channel — the alerts go to direct messages
verified_by: the helper (2026-08-23)
verified_on: 2026-08-27
---

# "I set it up in the channel and I see nothing"

The second most common message after onboarding. The person really does create
the monitor, does everything right, and then waits in
`#🖥️-use-vinted-bot-here` for items to start appearing there.

## Where that idea comes from

The Dashboard is **operated** in that channel, so it is natural to expect that
what the monitor finds will also be **shown** there. It is not. The monitor
watches the Vinted catalog through the link that was put into it, and when it
finds something it sends it to **Discord direct messages**.

Say it in exactly that sentence - that a monitor is not used in the channel, the
channel is only for operating the bot. Without that distinction the person
believes their monitor is broken, when it works and they are simply looking in
the wrong place.

## When there is nothing in the direct messages

Then go through it in order:

1. Do they have **messages from server members allowed** in Discord? This is the
   most common cause and it is described in the documentation too.
2. Is the monitor **active**, not paused?
3. Is the session **verified**?
4. Are the filters too narrow? That is checked through **Test Item** - paste a
   link to a specific item and the bot shows whether it passes the filters.

## When they get pings and do not know where from

It means they have **Mentions** enabled in the rule, which adds `@their name` to
the alert. It is not a fault, they just did not connect it with the monitor.
