---
id: bot-is-for-buying
title: Fyndit is a bot for buying — you cannot sell through it
verified_by: the helper
verified_on: 2026-09-08
---

# The answer to "can I also sell through the bot?" is no

Fyndit watches Vinted and helps you **buy** - monitors, alerts, offers, autocop.
Selling is not in it. Nobody uses it for selling.

This is **not a gap in the documentation**. It is an answer we know, and it can
be given normally, without the ⚠️ marker and without escalating.

## Why the model believes the opposite

There are three places in the corpus that look like selling and are not:

**1. The "Selling" session type.** The word does occur in the docs, but it is
only a switch that unlocks the wardrobe. It sells nothing.

**2. The Promote page** (`docs/promote`). It looks the most convincing, because
it talks about the wardrobe, points and a community channel. In reality it only
**collects a button for promoting listings that are already up on Vinted**. Its
own troubleshooting line gives it away: *"Wardrobe is empty — list items on
Vinted first."* Until a person has items listed on Vinted there is nothing to
promote. Promote therefore assumes a sale that happened elsewhere - it does not
make one.

On top of that **this feature does not currently work**. That is information for
the helper, not a sentence for a customer's answer; Promote must not be promised
as a route to selling.

**3. The reselling tutorial** (`tutoriels/resell-vinted`). The whole page is
about reselling, so it comes up first on the word "sell". But Fyndit's share in
it is described plainly: it watches Vinted and lets you buy before the others.
The onward sale the person makes themselves, on Vinted.

## How to say it

Short and without apologising: the bot is for buying - it finds listings and
helps you get them before the others. Selling does not go through it; that is
done directly on Vinted.

If they ask specifically about Promote, you can add that it only makes listings
they already have on Vinted more visible. Promise no more than that.

Related to [[watch-is-not-autocop]]: again an adjacent topic read as an answer.
The difference is that there the right reaction was to admit a gap - **here it is
not**, we know the answer.
