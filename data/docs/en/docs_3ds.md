---
source: https://www.fyndit.app/docs/3ds
title: 3D Secure Verification
---

# 3D Secure Verification

Handle bank verification prompts during purchases.

Some purchases on Vinted trigger a 3D Secure (3DS) verification step required by your bank. This is a bank security check, so the bot pauses and waits for you to confirm the purchase. You normally reach this step from a notification, not from a Dashboard panel.

## When 3DS Is Triggered

After the bot initiates a purchase, Vinted may respond with a 3DS verification requirement instead of completing the transaction immediately. This happens based on your bank's fraud detection rules and is not controlled by Fyndit or Vinted. When this happens, your notification embed turns orange and shows:

- **Verify 3DS button** - A link button that opens the 3DS verification page in your browser. Click this to complete your bank's authentication.
- **Countdown timer** - A Discord relative timestamp showing how much time you have left to complete verification. The timer is intentionally short (a few minutes) to ensure fairness for other users in the autocop queue.
- **Delivery information** - The delivery method, carrier, and pickup point or address, so you can confirm the purchase details before completing verification.
- **Total price** - The full amount that will be charged, including shipping fees.
- **Decline button** - If other users are waiting in the queue, a Decline button appears. Click it to cancel your purchase attempt and pass the opportunity to the next user.

## Completing Verification

1. Click the **Verify 3DS** link button on your notification embed.
2. Complete your bank's verification process (approve the push notification, enter the SMS code, or confirm in your banking app).
3. Once verified, Vinted completes the transaction and the bot updates your embed to green with the purchase details.
4. If the bot cannot edit the original message, it sends the result to you by DM.

## Timeout Behavior

If you do not complete 3DS verification within the allotted time, the bot checks whether the item is still available on Vinted:

- If the item is **no longer buyable** (someone else bought it, or your bank already approved it), the bot assumes your 3DS verification went through successfully and marks the purchase as a success. This handles the common case where verification completes but the bot's timer expires before receiving confirmation.
- If the item is **still available**, the bot assumes verification was not completed and your turn is skipped. The next user in the autocop queue is promoted and given their purchase attempt.

## Decline Button

The Decline button only appears when there are other users waiting in the queue behind you. Clicking it immediately cancels your purchase attempt and advances the queue to the next user. If you are the only user in the queue, no Decline button is shown (you can simply not complete the 3DS and let it time out).

**Warning** Complete 3DS verification as quickly as possible. The timeout is intentionally short to give other users in the queue a fair chance. Have your banking app ready before enabling autocop.
