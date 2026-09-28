---
id: delivery-speed
title: What actually decides who buys the item first
verified_by: the helper
verified_on: 2026-08-21
---

# Winning the race for an item

Practitioner knowledge from the team. The documentation says Pro has *priority
autocop*; this note is the level below that — what a customer can change on
their own side to be first, and what they cannot.

Comes up constantly: people lose an item by a second and ask whether a plan
would fix it.

## Payment method, fastest first

1. **Vinted balance** — money already in the Vinted wallet
2. **Credit card**
3. **Apple Pay**

This is about **how quickly Vinted registers the purchase intent**, nothing to
do with 3D Secure. Balance is already sitting in the wallet, a card has to be
charged, and Apple Pay takes a little longer still. The differences are small
but they decide races.

## Delivery method

**Home delivery is faster** than a pickup point, because there is no pickup
point to resolve during checkout. It is often more expensive, so say both.

If they stay on pickup, more eligible points means fewer stalls — widening the
radius or allowing a fallback beats forcing one favourite. Location has to be
set before any pickup point can be chosen at all.

## What speed cannot fix

None of this wins a race against someone with the same setup. That question —
the odds, and why there is no percentage — is [[autocop-win-chance]].

## 3D Secure is used on purpose, not avoided

Autocop buys blind — nobody has looked at the item. 3DS is what buys the time to
look: the purchase pauses at verification and the customer decides whether they
actually want it before approving.

So do not tell anyone to turn 3DS off to be faster. For competitive niches it is
the opposite of a problem.

### Two clocks, not one

This trips people up, so keep them apart:

- **Vinted holds the item for 15 minutes** while 3DS is pending. That is Vinted's
  behaviour, not a Fyndit feature — there is no "reserve the item" button.
- **Fyndit's own countdown is short**, a few minutes, and it is short on purpose.
  Miss it and your turn passes to the next person in the autocop queue.

So when a customer asks whether they can hold an item to inspect it: the pause is
real, but it comes from 3DS, and Fyndit's queue clock runs out well before
Vinted's hold does.

Also worth knowing: repeatedly cancelling purchases in one day can get the Vinted
account cooled down for about a day — that part is in the documentation.

That second one is exactly why the 3DS pause matters: **backing out at
verification is not the same as cancelling a completed purchase.**

## Multiple Vinted accounts

More connected accounts let the bot attempt the same item from several accounts
at once, which raises the odds of one of them getting through.

## New accounts get blocked

A freshly made Vinted account used straight away for buying is very likely to be
blocked. It needs warming up first — browsing, looking around, leaving it alone
for a while, coming back — over a few days.

This is Vinted's behaviour, not Fyndit's, so keep it to practical advice and do
not present it as something Fyndit controls or guarantees.

## Not true

- **There is no waitlist for Pro.** A ticket once looked like there was; there
  is not.
