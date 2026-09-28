---
source: https://www.fyndit.app/docs/language
title: Language Settings
---

# Language Settings

Configure the bot's display language for all messages and interface.

Fyndit supports multiple languages for its entire user interface. Every message, button label, embed title, modal prompt, and error message the bot sends is translated into your chosen language. Use the Dashboard first, or fall back to /preferences.

Open the Dashboard here: Open Dashboard

## Changing Your Language

Run /preferences and select your preferred language from the dropdown menu. The change takes effect immediately for all new messages.

**Tip** You can also change your language from the Dashboard: Open Dashboard

## Language vs. Domain

Your display language and your Vinted session domain are completely independent settings. For example:

- You can have the bot speak French while your sessions are connected to the German Vinted domain (vinted.de). The bot will talk to you in French, but your sessions will browse and buy from the German marketplace with prices in EUR.
- You can have the bot speak English while using a French session. Notifications will be in English, but the Vinted item data (title, description) remains in whatever language the seller wrote it in.

The language setting only affects how the bot communicates with you on Discord. It does not change which Vinted marketplace your sessions access, which currency prices are displayed in, or what language item titles/descriptions appear in (those come directly from Vinted sellers).

**Tip** If you change your language, only new messages will use the new language. Previously sent notifications and embeds will remain in the old language since they are already sent.

## What To Expect

- The Dashboard and slash command both update the same preference.
- Old notifications do not change after you switch languages.
- If some labels still appear in the old language, reopen the panel so it can refresh.
