---
id: invalid-monitor-link
title: "Invalid link" when adding a monitor
verified_by: the helper
verified_on: 2026-08-16
---

# "Invalid link" when adding a monitor

When a customer pastes a Vinted catalog URL into a monitor and gets an invalid
link error, check the **domain** first. It is the most common cause.

Fyndit accepts catalog URLs from the 26 supported country domains only. A link
from `vinted.com` does not work — that is the US storefront, and `com` is not
one of the domain codes.

**The fix is to edit the link, not to rebuild the search.** Swapping the domain
is enough:

```
https://www.vinted.com/catalog?...   ->   https://www.vinted.ro/catalog?...
```

Everything after the domain stays exactly as it is. The filter parameters
(`catalog[]`, `size_ids[]`, `brand_ids[]`, `status_ids[]`, `price_to`) are the
same across domains, so the search carries over untouched.

Tell them to change those few characters. Sending someone back to Vinted to
rebuild the whole search is unnecessary work — only suggest that if the edited
link still fails.

## What is not the cause

- **The currency parameter.** A link ending in `currency=RON` is fine. Prices
  are converted to the buyer's domain currency automatically, so the currency
  in the URL says nothing about whether the link is valid.
- **The filters themselves.** Category, size, brand, condition and price
  parameters carry over between domains; they do not need changing.

## Example

`https://www.vinted.com/catalog?...&currency=RON` from a Romanian customer
fails. The same search built on `vinted.ro` works.
