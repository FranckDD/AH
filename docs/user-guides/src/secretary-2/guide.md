---
title: Cash register, withdrawals and daily closing
role: Secretary
subtitle: Recording money that leaves the till, cancelling a sale or a withdrawal, and closing the cash register at the end of the day.
version: 26 October 2026
output: secretary-2-cash-withdrawals-closing
---

## Before you start {.unnumbered}

This is the second guide for the secretary. The first one covers patients and invoices. This one covers what happens to the money after it reaches the till: withdrawals, cancellations, and the daily cash closing that compares what you counted with what the system recorded.

The screenshots come from a demonstration account. Your screens show your own name and the real figures of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the secretary can do here

Under **Daily work** the menu holds three entries for this guide: Cashier, Withdrawals and Cash closing. With them you can record a withdrawal, cancel a withdrawal or a sale with a written reason, count the till and validate the closing, and ask for an adjustment after a closing.

You cannot start the cash register, change a closing once it is saved, or approve an adjustment. The administrator starts the register, and the promoter or an administrator decides on adjustments.

### How the closing works in one paragraph

The system adds up every payment, every withdrawal and every cancellation recorded since the previous closing. You count the notes and coins and copy the total of each mobile money statement. You do this without seeing the amount the system expects. When you validate, the system reveals its figures and the difference for each mode. A saved closing can never be edited.

### Interface language and connection

Select **EN** at the top right to work in English, as described in the first guide. The cash closing needs the connection to the server. Withdrawals and invoices can be entered offline and are sent later, but the closing cannot be started offline (see the chapter on the closing).

## Setting up the cash register (administrator)

Until the administrator has started the cash register, the Cash closing screen cannot be used. It shows a card titled **Till not set up** and nothing else.

![The Cash closing screen before the register is started](figures/not-configured.png)

1. Select [[Cash closing]] {1} in the menu.
2. Read the card {2}. It asks you to have an administrator set the opening cash float.
3. Tell the administrator. Come back to the screen once it has been done.

The administrator does this once, from the **Cash closings** screen of the administrator menu. The form asks for the cash float present in the till at that moment, then shows a warning before it saves.

![The administrator confirming the starting cash float](figures/admin-start.png "small")

The administrator types the amount {1}, selects the start button, reads the confirmation (here 50 000 FCFA, with the warning "this value can never be changed afterwards") and confirms. From that moment, the system counts every payment and withdrawal. Money recorded before this moment is never part of any closing.

> Caution: The starting float cannot be changed afterwards. The amount must be a real count of the notes and coins in the till at the time, not an estimate.

## Recording a withdrawal

A withdrawal is money that leaves the till for the needs of the centre: office supplies, a bill, a repair. Every withdrawal needs a reason, because the promoter reads these reasons when a closing shows a difference.

![The withdrawal list with its filters](figures/withdrawal-list.png)

The list opens on **Cash Withdrawals** with the most recent entry first. The search box {1} looks in the reasons. The **Status** filter {2} switches between active and cancelled withdrawals. Amounts appear in the **Amount** column {3} with a minus sign. The red button {4} at the end of an active row cancels it.

### Creating a withdrawal

1. In the menu, select [[Withdrawals]]. The same form opens from the **New withdrawal** quick action on the home screen.
2. Select [[New Withdrawal]] at the top right of the list.
3. Type the amount in [[Amount (FCFA)]] {1}. It must be greater than zero.
4. Choose a [[Category]] {2}: Supplies/Medicine Purchase, Salaries, Maintenance/Repairs, Utility Bills or Other. The category can be left empty, but a choice makes later reading easier.
5. Choose the [[Payment Method]] {3}: Cash, Orange Money, MTN Mobile Money or Other mobile money. It is required, and it must be the source the money really left from.
6. Write the reason in [[Justification]] {4}, in a sentence that a colleague can understand a month later.
7. Select [[Save Transaction]] {5}.

![The new withdrawal form](figures/withdrawal-form.png)

The withdrawal appears at the top of the list with the status **Active**.

> Note: In the list, the category column shows the raw code (SUPPLIES, BILLS, OTHER) instead of the English label chosen in the form. Older withdrawals entered in French show "Dépense". This does not change the amounts.

### Choosing the payment method

The payment method decides which line of the closing the withdrawal reduces. A withdrawal in Cash lowers the expected cash. A withdrawal in Orange Money lowers the expected Orange Money total, and so on. If the money left from the mobile wallet but you record Cash, the closing shows a difference on both lines. Choose the mode that matches the real source.

## Cancelling a withdrawal

A withdrawal cannot be edited. When one is wrong, you cancel it with a reason and, if the money really left, you record a correct one.

1. In the list of withdrawals, find the row. Use the search box {1} if the list is long.
2. Select the red button {4} at the end of the row.
3. The form **Cancel Transaction** shows the amount and the date. Type the reason in [[Justification]] {5}. The button stays grey until you write one.
4. Select [[Confirm Cancellation]] {6}.

![The cancellation form of a withdrawal](figures/withdrawal-cancel.png)

The row leaves the Active list. Filter the **Status** on **Cancelled** to find it again: its amount is struck through and its status reads **Cancelled**.

![A cancelled withdrawal in the Cancelled filter](figures/withdrawal-cancelled.png)

A cancelled withdrawal no longer counts in the closing: the money is back in the expected total as if it had never left.

> Caution: The cancellation form says "A cancelled invoice cannot be restored", although it is a withdrawal. The meaning is the same: a cancellation cannot be undone. If you cancel by mistake, record a new withdrawal.

## Cancelling a sale

Cancelling a sale is done in the Cashier screen, with the last button of the invoice row, and the first guide describes the row buttons. It matters here because the cash register treats a cancelled sale as money handed back.

![The cancellation form of a sale](figures/sale-cancel.png "small")

1. Select [[Cashier]] in the menu and find the invoice.
2. Select [[Cancel]] at the end of the row.
3. Type the reason in [[Justification]] {1}. Name the cause and say how the patient was repaid.
4. Select [[Confirm Cancellation]] {2}.

The sale stops appearing in the Active list. At the closing, the amount paid on that sale counts as an exit for the payment mode it was received in, and the sale is listed by number in the section **Sales cancelled during the period** with your user name and your reason. Management reads that section, so the reason must be true and specific.

> Caution: Cancel a sale only when the money was really handed back to the patient. If you cancel but keep the cash, the closing expects less money than the till holds, and the difference appears on your name.

## The daily closing

The closing is the last task of the day. You count the till, you copy the statement of each mobile money operator, and the system tells you how the figures compare.

### Before you count

Do these things before you open the closing screen:

1. Enter every invoice, payment and withdrawal of the day. Anything entered after the closing falls in the next period.
2. Check that the connection indicator at the top right reads **Connected**. The closing refuses to start while entries made on this computer are still waiting to be sent, and while the computer is offline.
3. Count the notes and coins in the till. Write the total on paper.
4. Read the total received on each mobile money statement (Orange Money, MTN Mobile Money, other). Write down a total for each, 0 when nothing was received.

Count first and open the screen afterwards. The screen does not show what is expected, so there is nothing to adjust your count to, and that is deliberate.

### Counting and validating

![The counting form](figures/closure-form.png)

1. Select [[Cash closing]] in the menu. The page title **Count** shows the date of the last closing, or "First closing of this till" the first time.
2. Type the cash total in [[Cash counted]] {1}. Use a comma or a point for cents and no thousands separator: write 54500, not 54 500.
3. Leave the comment {2} empty if nothing is unusual. The comment is optional until the system finds a difference on that mode.
4. Type the statement total of each mobile money operator in its field, for example {3} for Orange Money and {4} for MTN Mobile Money. Every field must hold a number. Write 0 when there is nothing.
5. Select [[Validate the closing]] {5}.

The button stays grey while a field is empty or invalid. The yellow message above it says which one.

### When your count differs from the system

If the cash total, or any mobile money total, differs from what the system expected, the closing is refused once and asks for a comment on that mode. The screen does not say by how much.

![The comment required after a difference was found](figures/closure-gap.png)

1. Read the red message {2}. It names the mode, here Cash.
2. Write in the comment box {1} what you think explains the difference: change given and not recorded, a note found in the drawer, a payment taken in another mode. Be factual.
3. Check the count itself before you validate again. A miscounted pile of notes is the most common cause.
4. Select [[Validate the closing]] {3} again.

> Caution: Do not retype different totals to find the amount the system wants. Each refusal is recorded in the audit log together with the period it belongs to, and management reads that trail.

### Reading the result

Once the closing is accepted, the screen shows what the system expected.

![The result of a closing, by payment mode](figures/closure-result.png)

The banner {1} confirms that the closing is saved. The table gives one line per mode. **Opening** {2} is the cash in the till at the start of the period. It is the cash you counted at the previous closing, or the starting float for the first one. Mobile money has no opening amount, so the column reads "Not applicable". **Expected** {3} is the opening plus the entries minus the exits, and **Counted** {4} is the amount you typed. The last column {5} states the difference in words: "No difference", "Difference of 500 FCFA over" or "Difference of 500 FCFA short".

**Entries** are the payments received, and **Exits** are the withdrawals and the sales cancelled during the period. Below the table, the screen lists the sales cancelled in the period and any adjustment that was applied.

The figure shows the second closing of the demonstration day. The first one had left 55 000 FCFA counted in the till, so that is the opening. One withdrawal of 1 000 FCFA went out, so 54 000 FCFA were expected. The till held 54 500 FCFA, which gives a difference of 500 FCFA over, explained in the comment.

The first closing of that day worked the same way. The opening was the starting float of 50 000 FCFA. Two cash payments (10 000 and 4 000) came in, and 7 000 FCFA went out: a withdrawal of 3 000 and the cancelled sale of 4 000. A withdrawal of 1 500 FCFA cancelled earlier did not appear in the figures at all. The cash expected was 57 000 FCFA and 55 000 FCFA were counted. The Orange Money line received 8 000 and paid out 5 000 for a bill, so 3 000 were expected, and the statement said 3 000.

### A closing cannot be changed

A saved closing has no edit and no delete button, for you or for anyone else. Reopening the Cash closing screen shows a new empty count for the next period, with the time of the previous closing at the top. The next period starts exactly where the previous one ended, so no payment is counted twice or skipped.

> Note: You can validate more than one closing in a day. Each one covers the time since the previous one. The promoter sees them all, one line each, in the closings list.

### Requesting an adjustment

When you find after the closing that a figure was wrong, for instance the 500 coin of the example belongs to someone else, you do not edit the closing. You send an adjustment request from the result screen.

![The adjustment request form](figures/correction-form.png)

1. At the bottom of the result screen, select [[Request an adjustment]].
2. Choose the mode concerned {1}.
3. Type the amount in [[Adjustment amount (FCFA)]] {2}. A plus amount adds money, a minus amount removes it: -500 removes 500 FCFA.
4. Write the reason in {3}.
5. Select [[Send the request]] {4}. The screen answers that the request waits for the promoter or an administrator.

The promoter or an administrator approves or rejects the request from the closings screen. An approved adjustment does not change the closing already saved. It is counted in the next period as an entry (positive amount) or an exit (negative amount), and the next result lists it under **Adjustments applied to this period**.

![The next closing, listing the approved adjustment](figures/closure-adjusted.png)

In the demonstration, the adjustment of -500 FCFA was approved and the next closing expected 54 000 FCFA in cash: the 54 500 FCFA counted before, minus the 500 FCFA adjustment. The count of 54 000 FCFA matched, with no difference.

## When the closing is forgotten

Every day at 23:00 (Cameroon time), the system closes the register by itself for any day that has no closing. This automatic closing records the expected amounts and counts nothing. It is marked as not declared, and the promoter and the administrators are notified of it.

The automatic closings of missed days are made when anybody opens the Cash closing screen or when the scheduled job of the server runs. If a day was missed, you will not see an error: the missed days are closed first, and your count then covers the time since the last of them. A day that already has your manual closing is never closed a second time.

Because nothing was counted on an automatic closing, the cash opening of the next period is the expected cash, not a counted amount. When that happens, the result of the next closing says "The cash opening balance comes from an automatic closing: it had not been counted."

> Note: A forgotten closing is visible to management and counts against nobody's figures, but it removes the daily check. Close before you leave, even when the day was short.

## Working without a connection

Withdrawals, invoices and cancellations can be entered while the computer is offline, as described in the first guide. They are kept on the computer and sent later.

The closing cannot. When the computer is offline, the Cash closing screen shows the message below and offers no count.

![The Cash closing screen while the network is down](figures/closure-offline.png)

The indicator {1} reads "Offline (your entries are saved)" and the screen says that it could not load the closing status {2}. Wait for the green **Connected** indicator and reopen the screen. In the same way, the closing is refused while entries made on this computer are still waiting to be sent, because those entries would be missing from the system totals and would create a false difference.

## Common mistakes

**Counting after looking at the sales.** The screen hides the expected amounts so that the count stays honest. Count the till first, then open the screen.

**Recording a withdrawal in the wrong mode.** A bill paid from the mobile wallet and recorded as Cash creates a difference on cash and one on the mobile line. Choose the mode the money really left from.

**Cancelling a sale without handing back the money.** The closing assumes the money was returned. The difference falls on the cash line, with your name on the cancellation.

**Typing the amount with a thousands separator.** Write 54500 or 54500,50. A space inside the number makes the amount invalid and the button stays grey.

**Entering the day's last payments after the closing.** They fall in the next period. Finish the cashier work before you close.

**Using the comment to hide a difference.** The comment is read by the promoter. Describe what you know; write that you do not know when you do not.

**Leaving the closing to the automatic job.** It produces a closing that counted nothing, and it removes the check on the day's cash.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Till not set up" | The administrator has not started the cash register | Ask an administrator to set the opening float. |
| "Unable to load the closing status" | The computer is offline or the server did not answer | Wait for the Connected indicator and reopen the screen. |
| "Operations entered on this device are still waiting to be sent" | Some entries have not reached the server | Wait until the synchronisation ends, or open Sync failures if an entry was refused. |
| "A difference was found on Cash. Explain it in its comment" | Your count differs from the expected amount | Check the count, write a factual comment, validate again. |
| "Comment required for: Cash" | The mode listed has a difference and an empty comment | Fill the comment of that mode. |
| "Invalid amount: a positive number, two decimals at most" | The amount contains a space, a letter or too many decimals | Retype the amount without separators. |
| "The closing was not saved ... The screen was reloaded" | Another closing was validated in the meantime | Count again and validate again. |
| Validate the closing stays grey | A field is empty, or a comment is required | Read the yellow message above the button. |
| Save Transaction stays grey on a withdrawal | The amount, the payment method or the justification is missing | Fill the three required fields. |

## Glossary {.unnumbered}

Adjustment
: A request, after a closing, to add or remove an amount on one payment mode. It is decided by the promoter or an administrator and counted in the next period.

Automatic closing
: A closing made by the system at 23:00 for a day that has no manual closing. Nothing is counted on it.

Blind count
: The way the closing works: you enter your count without seeing the amount the system expects.

Cash float
: The amount of cash in the till when the register is started. Only an administrator sets it, once.

Closing
: The comparison, for one period, between what the system recorded and what was counted.

Difference
: Counted amount minus expected amount. Over means more money than expected, short means less.

Expected
: The opening amount plus the entries minus the exits of the period.

Period
: The time between two closings. The first one starts when the register is started.

Withdrawal
: Money that leaves the till for the needs of the centre, recorded with a mode and a reason.
