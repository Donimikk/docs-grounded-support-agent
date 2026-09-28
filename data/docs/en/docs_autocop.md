---
source: https://www.fyndit.app/docs/autocop
title: Autocop
---

# Autocop

Automatically purchase items the moment they match your monitors.

Autocop is Fyndit's automatic purchasing system. When enabled, the bot immediately tries to buy an item the moment it matches your monitor filters. Use the Dashboard first to manage it from your monitor rules. The fallback command is /monitors.

Open the Dashboard here: Open Dashboard

## Enabling Autocop

Autocop is controlled through the Rules system. To enable it:

1. Open your monitor or group from the Dashboard.
2. Click **Rules**.
3. Click **Add Rule**.
4. Choose **Autocop**.
5. Turn the rule on.

You can combine autocop with scheduling (specific days/hours), price conditions, and usage limits. See the Rules section for full details.

## How It Works

1. A new item appears on Vinted that matches one of your monitors with an autocop rule active.
2. The bot chooses one or more compatible sessions, then sends the purchase request.
3. If the purchase succeeds, you get a success update with the order details.
4. If the purchase fails, the bot shows the reason and either retries through the queue or stops there.

## The Queue System

When multiple users have autocop enabled on monitors that match the same item, a queue is automatically formed. The queue determines the order in which users get their purchase attempt:

- **Position 1** - The first user gets an immediate purchase attempt. If it succeeds, the item is bought and all other users are notified that the item has been taken (red embed).
- **Positions 2+** - Other users see their current queue position (e.g. "Position 2/5") displayed in their notification embed. They can monitor the queue in real-time as positions update.
- **Automatic promotion** - If the current user's purchase fails, is declined, or times out (3DS verification), the next user in the queue is automatically promoted and given their attempt. Their embed updates to "Your turn" status.
- **Leave queue** - Users can voluntarily leave the queue at any time by clicking the **Leave Queue** button on their notification embed. Their embed is updated to a neutral gray state.
- **Item taken** - When the item is successfully purchased by any user, all remaining users receive an updated embed indicating the item is no longer available.
- **Report item** - Users in the queue can report suspicious items (see Reporting section), which removes them from the queue and warns other users.

## Manual Buy (Without Autocop)

If autocop is not enabled on the matching monitor, pressing the **Buy** button on a notification creates a new queue entry and immediately tries the purchase. The flow from that point is the same as autocop: the bot handles session selection, 3DS if needed, and reports the result.

## Purchase Results

After a purchase attempt, the notification embed is updated:

- **Success (green)** - Transaction ID, delivery method (pickup point name or home address), carrier name, and total price including shipping fees.
- **Failure (red)** - The error reason. Common failures: item already sold, payment method declined, insufficient wallet balance, session token expired, carrier not available, no eligible sessions found.
- **3DS Required (orange)** - The purchase requires 3D Secure bank verification. See the 3D Secure section.
- **No sessions (red)** - No sessions were available to attempt the purchase. Ensure you have at least one authenticated, non-selling session on a compatible domain (and if your rule uses a session group, make sure the group contains eligible sessions).

**Warning** Autocop purchases are real transactions on Vinted. Make sure your payment method has sufficient funds and your shipping configuration is correct before enabling autocop rules.

## Troubleshooting

- **"No sessions" error** - You need at least one active, authenticated session that is not of type "Selling" on a compatible domain (and included in your rule’s session group if you set one).
- **"Payment method is not available" error** - Vinted may require your account to complete its first payment manually. Make a purchase manually on Vinted with a credit card, then retry autocop.
- **"Access denied" error** - Vinted refused the purchase for that account. This usually means the account is blocked by the seller, or Vinted has temporarily limited the account from buying for roughly 24 hours. Try buying any item manually on Vinted with the same account. If the manual purchase also fails, stop autocop attempts and let the Vinted account rest for a while. This cooldown can happen after too many buy attempts in a short time, or too many cancelled purchases in the same day.
- **"Unclear checkout error" / `dynamic` error** - Vinted returned a generic checkout failure. A common cause is that the item cannot be shipped to your session's region. Check the item manually on Vinted or retry with a compatible region/session.
- **Purchase fails immediately** - The item may have already been sold before the bot could buy it. This is normal for extremely popular items. Using multiple sessions (and enabling Multi-cop) can increase your chances.
- **Autocop not triggering** - Verify the rule is enabled, the rule's schedule allows the current day/time, the rule has not reached its maximum uses, and the rule has not expired.
