---
source: https://www.fyndit.app/docs/session-pools
title: Session Groups
---

# Session Groups

Group sessions to control which accounts automation can use.

Session groups let you bundle multiple Vinted sessions into a named set (for example: "Main Buyers", "FR Only", "Backups"). Rules can then be told to use a specific session group, so autocop, autooffer, and autolike only run on the accounts you choose. Use the Dashboard first, or fall back to /session_groups if needed.

Open the Dashboard here: Open Dashboard

**Tip** If you previously used “session pools”, session groups are the replacement. The workflow is simpler: create a group, add sessions, then select it on a rule.

## Creating a Session Group

1. Open the Dashboard and choose **Session Groups**, or use /session_groups.
2. Click **Create Group** and give it a name.
3. Open the group, then click **Add Session** to attach one or more existing sessions.

**Tip** You can also manage session groups from the Dashboard: Open Dashboard

## Using a Session Group in Rules

1. Open a monitor or group from the Dashboard, or use /monitors.
2. Click **Rules**, then select or create a rule.
3. Set the rule's **Session Group** to the group you want.

If no session group is selected, the bot falls back to using any compatible session on your account.

## Notes

- For buying automation, **Selling** sessions are ignored.
- Autocop rules can also set a **dead time** (cooldown in seconds) so sessions that fail are temporarily skipped.
- Manual buttons (Buy/Offer/Favorite) do not ask you to pick a group; they simply use a compatible session.

## Troubleshooting

- **"No sessions" / "No compatible session"** - You do not have a usable session for that seller’s country/domain, or all eligible sessions are archived/uninitialized. Create/authenticate a session on the right domain.
