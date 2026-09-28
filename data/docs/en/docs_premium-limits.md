---
source: https://www.fyndit.app/docs/premium-limits
title: Roles, Permissions & Limits
corrected: 2026-08-28 Autocop a auto-offer su LEN na Pro, nie na Plus. Tato
  stranka tvrdila 'Included' aj pri Plus a odporovala tym home_pricing.md,
  ktora ma 'no' - a spravna je cenova tabulka. Overil the helper, ktory to predava.
  Bez tejto opravy si model vyberal a zakaznik na Plus by cakal autocop.
---

# Roles, Permissions & Limits

Understand roles, permissions, tier limits, and what happens when your role changes.

Fyndit uses a role-based system with granular permissions and limits. Your role determines what actions you can perform and how many resources you can have active at the same time. Open the Dashboard first if you want to check your current usage; use /my_info as the fallback command.

## Tier Comparison

Each role grants a fixed set of limits. These limits apply to active, non-archived items only.

| What you get | Free | Plus | Pro |
| --- | --- | --- | --- |
| Vinted sessions | No sessions. You can browse the interface, but you cannot run a full buying setup. | 1 session. Enough for one main Vinted account. | 20 sessions. Best if you manage multiple accounts or marketplaces. |
| Monitor groups | 1 group. | 10 groups. | Unlimited. |
| Monitors | 1 monitor. | 50 monitors. | Unlimited. |
| Autocop / auto-offer / auto-like | Not included. | Not included. | Included. |
| Hidden-item access | Not included. | Included. | Included. |
| Webhooks | Not included. | Not included. | 20 webhooks for sending alerts to multiple Discord channels. |
| Support level | Standard help only. | Standard help only. | Priority support. |
| Best for | Trying Fyndit and learning the layout. | One serious personal setup for buying and tracking items. | Heavy users who want many setups, more automation, and webhooks. |

**Tip** The easiest way to think about it: Free lets you try the app, Plus gives you a full personal buying setup, and Pro gives you more of everything.

**Tip** Some accounts may have custom limits that override the default tier. Those limits can stay in place through a role change if they are not cleared.

## Role Sync

Your Fyndit tier is derived from your Discord roles via a mapping system. Each Discord role can be mapped to a Fyndit tier with a priority value; if you have multiple Discord roles mapped, the highest-priority mapping wins.

Role sync happens automatically when your Discord roles change. If your role looks wrong, contact staff in the server.

## What Happens on Downgrade

When your role is downgraded (for example from Plus to Free):

1. Your tier is updated and any custom limit overrides are cleared unless they were kept.
2. The bot calculates your new limits based on your updated role.
3. For each resource type (sessions, groups, monitors, webhooks), if your active count exceeds the new limit, the bot archives the oldest excess items.
4. You receive a DM summarizing the role change and listing exactly how many items were paused.

## Archived Items

When an item is archived due to a downgrade:

- It is flagged as inactive and excluded from all automation.
- Archived sessions, monitors, groups, and webhooks are paused but **not deleted**. All configuration is preserved.

**Warning** Archived items are not deleted. They remain in your account but are paused and inactive. No monitoring, autocop, or any other automation runs on archived items.

## Unarchiving Items

You can unarchive any item at any time, but only if your active count for that resource type is below your limit.

1. Open the management panel for the item.
2. Use the archive/unarchive toggle.
3. If blocked, archive or delete another active item first to free a slot.

## Creating New Items at the Limit

The same limit checks apply when creating new items. If you are at your limit, the bot rejects the request until you archive or delete an existing item.

## Upgrading Back

On upgrade, your limits increase immediately. Previously archived items remain archived; you choose which to unarchive manually.

**Tip** Use /my_info to see your current usage versus your limits at any time.

**Tip** You can also check your limits from the Dashboard: Open Dashboard

## What This Means In Practice

- Free users can browse the interface, but they do not get a real buying setup.
- Plus is the full everyday plan: one account, one main setup, buying automation, and enough monitors for normal use.
- Pro is the power-user plan: more sessions, more monitors, webhooks, and the highest limits.
