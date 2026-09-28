---
source: https://www.fyndit.app/docs/offers
title: Offers
---

# Offers

Send price offers to sellers directly from Discord.

The Offer feature lets you negotiate prices with sellers without leaving Discord. Open the notification from the Dashboard or from your DMs, then use **Offer**. There is no separate slash command for this flow.

After the seller accepts, the offer turns into a normal purchase flow and you will get a follow-up update with the result.

## Sending an Offer

1. Click the **Offer** button on any item notification embed.
2. A modal appears with a price input field. The placeholder shows the current item price for reference.
3. Enter your desired offer price (use a dot for decimals, e.g. `15.50`) and submit.
4. The bot sends the offer using a compatible session.
5. If the offer is sent, you get a confirmation message and usually a conversation button so you can keep talking to the seller.

## Session Selection for Offers

When sending an offer, the bot uses the first compatible session it can use to reach the seller's country or domain.

If no compatible session is found, the bot shows an error saying it cannot reach the seller's marketplace. That usually means you need a session on a different domain.

## After the Seller Accepts

If the seller accepts your offer, the bot continues with the purchase for you:

- You may get a success message with the transaction details.
- If your bank needs to verify the charge, you will get a 3DS prompt.
- If the purchase fails, the bot tells you why and keeps the conversation link available when possible.
- If the original message cannot be edited anymore, the bot sends the accepted-offer update by DM instead.

## Automatic Offers via Rules

You can automate offers through the Rules system. Create a rule with the **Autooffer** action and specify the offer percentage (1-99%). When an item matches your monitor and the rule is active, the bot automatically calculates the offer as a percentage of the listed price and sends it to the seller. For example, setting 80% on an item listed at 50 EUR sends an offer of 40 EUR.

**Tip** Vinted has minimum offer thresholds. Your offer must typically be at least 40% of the listed price for the seller to receive it. The bot will report an error if your offer is below the platform minimum.

## Troubleshooting

- **Offer fails with error** - The most common cause is that the offer price is below Vinted's minimum threshold (approximately 40% of the listing price). Try a higher amount.
- **"No compatible session"** - You do not have an authenticated session on a domain that can interact with the seller. Create a session on the appropriate domain.
- **Offer sent but no conversation link** - This can happen if Vinted does not return the conversation id. The offer was still sent; check your Vinted messages manually.
- **Seller accepted but nothing changed yet** - Keep DMs on. The follow-up may arrive as a DM if the original notification can no longer be edited.
