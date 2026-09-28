---
source: https://www.fyndit.app/docs/rules
title: Rules
---

# Rules

Automate actions with scheduling, limits, and expiration.

Rules are the automation engine of Fyndit. A rule defines what the bot should do automatically when an item matches a monitor. Open the monitor or group from the Dashboard first, then use **Rules**. The fallback command is /monitors.

Rules can be attached to individual monitors or to groups, where they apply to all monitors in the group. Each rule can include actions, scheduling, price conditions, and usage limits.

## Available Actions

Each rule can trigger one or more of the following actions simultaneously:

- **Autocop** - Automatically purchase the item. The bot uses your sessions (optionally restricted by a session group) and enters the autocop queue. This is the primary action for automatic buying.
- **Autooffer** - Automatically send a price offer to the seller at a configured percentage of the listed price. When you add this action, a modal appears asking for the percentage (1-99%). For example, 80% on a 50 EUR item sends an offer of 40 EUR.
- **Autolike** - Automatically like the item on Vinted. Adds the item to your Vinted wishlist. The favorite button on the notification also updates to reflect the liked state.
- **Mentions** - Send a mention ping (`@you`) in the notification message. By default, notifications are sent without a ping. Enabling mentions ensures Discord sends a push notification to your device, useful for high-priority monitors.

You can enable multiple actions on the same rule. For example, a rule with both Autocop and Mentions will ping you and attempt to buy the item simultaneously.

## Creating and Managing Rules

1. Open a monitor or group management panel.
2. Click **Rules** to open the rules panel.
3. Click **Add Rule** to create a new rule. Rules are created in a disabled state with no actions.
4. Select actions from the dropdown. Actions can be added or removed at any time.
5. Toggle the rule to enabled when ready.

## Session Group (Optional)

Rules can be linked to a **session group**. When set, the rule only uses sessions inside that group for automation actions. If not set, the bot falls back to any compatible session on your account.

## Autocop Advanced Settings

When you add Autocop to a rule, you may be asked to configure:

- **Multi-cop** - Lets multiple sessions or accounts try the same item at the same time, so you can increase your chances of winning the purchase.
- **Count** - How many sessions to try in multi-cop (leave empty for automatic).
- **Session dead time** - Cooldown (seconds) applied to sessions that fail, so they are temporarily skipped.

## What The Buttons Mean

- **Toggle** - Turns the rule on or off.
- **Hours** - Sets the time window when the rule is allowed to run.
- **Limits** - Sets how many times the rule can fire before it stops.
- **Configure Autocop** - Opens the extra buying settings for Autocop.
- **Price** - Adds a minimum or maximum price rule.
- **Delete** - Removes the rule.

## Scheduling

Rules can be restricted to specific time windows:

- **Active Days** - Select which days of the week the rule is active (Monday through Sunday) using the day dropdown. On unselected days, the rule is completely ignored even if items match. By default, all 7 days are selected.
- **Active Hours** - Click **Hours** to set a start time and end time in `HH:MM` format. The rule only triggers between these hours. By default, the window is `00:00` to `23:59` (all day).
- **Timezone** - Set your timezone so the schedule uses your local time. Use standard timezone names like `Europe/Paris`, `America/New_York`, `UTC`, etc. The default is `UTC`.

Days and hours work together. For example, you can create a rule that only runs on weekdays (Mon-Fri) between 09:00 and 18:00 CET, so autocop does not run while you sleep or on weekends.

## Price Conditions

Click **Price** on a rule to add a price condition. This restricts the rule to only trigger when the item price meets a specific threshold:

- **lte** (less than or equal) - The rule only fires if the item price is at or below the specified value. Example: `lte 50` means only items priced 50 or less.
- **gte** (greater than or equal) - The rule only fires if the item price is at or above the specified value. Useful for avoiding suspiciously cheap items.
- **eq** (equals) - The rule only fires if the item price exactly matches the specified value. Rarely useful but available.

The price value is in the currency of your session domain. Leave both fields empty to remove the price condition.

## Limits and Expiration

Click **Limits** to control how many times a rule can fire and when it stops:

- **Maximum Uses** - Set a maximum number of times the rule can trigger. After reaching this limit, the rule is automatically disabled and the bot sends you a DM notification. For example, set to 1 for a one-shot autocop that buys the first match and stops. Leave empty for unlimited.
- **Expiration Date** - Set a date and time (format: `YYYY-MM-DD HH:MM`) after which the rule is no longer active. When a rule expires, the bot notifies you via DM.
- **Current Usage** - The rule panel shows how many times the rule has been used out of its maximum. You can reset the counter by updating the max uses.

## Rule Priority and Inheritance

When both a group-level rule and a monitor-level rule exist for the same monitor, the monitor-level rule takes precedence. This lets you set a default behavior on the group (e.g. autolike all matched items) and override it for specific monitors (e.g. autocop on your highest-priority monitor).

Rules are evaluated per-item. If multiple rules match an item, all their actions are executed. Actions from different rules stack (e.g. if one rule has Autolike and another has Mentions, both happen).

**Tip** When a rule reaches its maximum uses or expires, the bot sends you a DM notification so you know automation has stopped. Check your rules periodically to ensure they are still active.

## Troubleshooting

- **Rule is not triggering** - Check that the rule is enabled (green toggle). Verify the current day and time fall within the schedule. Check if the rule has reached its max uses or has expired.
- **Invalid max uses** - The value must be a positive integer.
- **Invalid price condition** - The operator must be exactly `lte`, `gte`, or `eq` (lowercase). The value must be a valid number.
- **Timezone not recognized** - Use standard IANA timezone names like `Europe/Paris`, not abbreviations like `CET`. You can find your timezone name at timeanddate.com.
