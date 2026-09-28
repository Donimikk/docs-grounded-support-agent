---
id: pickup-point-name-clash
title: When pickup points behave differently from how they are set
verified_by: the helper
verified_on: 2026-08-28
---

# Pickup points do not follow the settings

The customer has a favourite point set, added another to the excluded list, and
the parcels still go somewhere else. Or they get **"Pickup point configuration
failed"**.

## What to advise first

Have them set it up again from scratch, in this order:

1. Delete **all** pickup points — favourites and excluded alike.
2. Set the **location**.
3. Only then add the **favourite pickup point**.

The order matters: without a location the bot has nothing to choose points
from, and a configuration layered on old remnants behaves unpredictably.

**If that does not help, we escalate to the team.** Do not dig further and do
not invent causes - with pickup points it has already turned out once that the
fault was on the system's side and a helper would never have guessed it.

## What not to say

Do not tell them they set something up wrong. Usually they did not.

And do not start explaining why it happens. The cause tends to lie in how the
bot processes the points, and that is a matter for the owner - not something a
customer should fix by toggling settings.
