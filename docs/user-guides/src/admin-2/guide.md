---
title: Oversight, approvals, cash register and settings
role: Administrator
subtitle: Deciding discount and stock requests, supervising the cash closings, reading the reports and logs, and keeping the centre's settings right.
version: 27 October 2026
output: admin-2-oversight-approvals-settings
---

## Before you start {.unnumbered}

This is the second guide for the administrator. The first one covers your own sign-in, the staff accounts, the exam and product catalogue and the prices. This one covers what you supervise once the centre is running: requests that wait for your decision, the cash register, the daily control, the settings that only you can change, and the logs.

The screenshots come from a demonstration installation. Your screens show the real data of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures. The people and records used in the figures are test data.

### What you decide, and what you only read

Some screens wait for a decision from you. Others are read-only, and a few hold settings that nobody else can change.

| Screen in the menu | What you do there |
|---|---|
| Pending discount requests | Approve or refuse a discount asked for you by a secretary |
| Discount history | Read every request, with its decision |
| Staff discounts | Set the automatic staff discount rules and the list of staff members |
| Stock management, Adjustment requests | Approve or refuse stock corrections and restocks |
| Stock management, Stock count | Set how often products must be counted, read the history |
| Cash closings | Start the cash register, decide adjustment requests, read closings, manage payment modes |
| Reports | Read the daily check and the figures, export a PDF, set two thresholds |
| Production, Production tracking | Set the loss tolerance and the delay of the batch alert |
| Financial Management | Read the ledger and record a manual income or expense |
| Audit & Security | Read the action log and the connection history |
| System Configuration | Identity of the centre, print token, and two reference lists |

The accounts, the catalogue and the prices are in the first guide.

### Notifications

The bell at the top right of every screen counts what is new for you. Select it to read the list.

![The notification list](figures/bell.png "small")

Select the bell {1} and read the entries from the top {2}. The entries you receive include: a request for a stock adjustment, a request for a discount, a cash adjustment request from a secretary ("Cash adjustment requested for the closing of ...: To decide."), the result of a cash closing that has a difference, a point of the daily check (the entry starts with the word Anomaly), and, for the production inputs, "Input ... is below its alert threshold". Selecting an entry marks it as read and opens the screen that deals with it, when there is one. A short message also appears at the top right when new entries arrive, and closes by itself.

The connection indicator at the top shows **Connected** while the server answers. If the network drops it reads **Offline**. On a wide screen it adds "(your entries are saved)", which does not apply to your role: nothing is kept on the computer. The screens of this guide, which all need the server, show a message ("Cannot load the data while offline. Figures shown would not be reliable.", or "Cannot load the data. Try again." when the server does not answer) with a **Retry** button instead of empty tables or zeros. Select **Retry** once the connection is back.

## Discount requests

A secretary cannot change the price of a catalogue item. When a patient asks for a lower price, the secretary sends a discount request to a manager of their choice, and the invoice stays locked until the manager decides. You are one of the two managers, the other being the promoter.

You only see the requests addressed to you. A request sent to the promoter does not appear in your list and you cannot decide it, although it appears in the history.

### Deciding a request

Select [[Pending discount requests]] in the menu. Each request is a card with the invoice amount at the top, the patient, a short summary of the lines and the name of the secretary.

![One request with 20 percent chosen: Refuse is greyed and Clear my choice is offered](figures/discount-card.png "small")

1. Read the card. The amount is the full price before any reduction.
2. To grant a percentage, select one of the four buttons {1}: 10%, 20%, 50% or 100%. No other percentage exists.
3. To grant time to pay instead of, or as well as, a reduction, choose a date in [[Deadline (installment plan)]] {2}.
4. Type your own password in [[Confirm with your password]] {3}. The password proves that the decision is yours.
5. Select [[Approve]] {4}, or [[Refuse]] {5}.

The card disappears and the secretary is notified. Three outcomes were checked on an invoice of 25 000 FCFA:

| Decision | Result on the invoice |
|---|---|
| Approved at 20% | The invoice becomes 20 000 FCFA and the history shows a reduction of 5 000 FCFA |
| Approved with a deadline only | The invoice stays at 25 000 FCFA, to be paid by instalments before the date |
| Refused | The invoice is released at its full price of 25 000 FCFA |

An approval must grant a percentage or a deadline, and a refusal must carry neither. If you select nothing, the card answers "An approval must grant a percentage and/or a due date." A wrong password gives "The password you entered is incorrect." in red under the fields. After five wrong passwords within a minute the card refuses further tries for a minute.

A refusal must carry neither a percentage nor a deadline. When you have selected one of them, the [[Refuse]] button is greyed and the card says "To refuse, first clear the percentage and deadline you picked." with a button **Clear my choice** {6}. Select it, then refuse.

> Caution: A refusal does not cancel the invoice. It releases the invoice at the full price, and the secretary then collects the money or cancels the invoice. The percentage always applies to the full price, not to a price already reduced by a staff discount, and an approved percentage replaces any automatic staff discount on that invoice.

### Reading the history

[[Discount history]] lists every request, whoever it was addressed to. It is read-only.

![The discount history and its indicators](figures/discount-history.png)

The four tiles {1} count the approved, refused and pending requests and give the total amount reduced for the period. The buttons {2} choose This week, This month or Custom dates, and the date fields set the range. The Status filter {3} narrows the table to one outcome. The column {4} shows the amount reduced, which stays empty when only a deadline was granted.

A request that stays Pending for days usually sits in the list of the other manager. Ask the promoter to decide it, or ask the secretary to cancel it and send it again to you.

## Staff discounts

The hospital grants an automatic reduction to its own staff. The rules and the list of staff members are kept in [[Staff discounts]], which you share with the promoter.

![The rules by category and the staff members](figures/staff-rules.png)

A rule belongs to a category of invoice line: Medications, Exams, Consultations, Booklets or Other care. It has a minimum invoice amount {1}, a rate in percent {2} and an Active box {3}. A rule applies when the invoice total reaches the minimum. In the demonstration data the Exams rule gives 15% from 2 000 FCFA and the Medications rule gives 10% from 3 000 FCFA.

To change a rule:

1. Edit the minimum or the rate on the row of the category.
2. Tick or untick [[Active]] {3}.
3. Select [[Save]] {4} on the same row. The row answers "Rule saved."

Each row has its own Save button, and it saves that row only. The rate must be a whole number from 1 to 100: a rate of 0 is refused with a message under the row.

To mark a person as staff:

1. Type at least two letters of the name or code in [[Search a patient]] {5}.
2. Select [[Mark as staff]] {6} on the right row. The person appears in the list of staff members below.
3. To withdraw the reduction, select [[Remove]] on the same person.

The person must exist as a patient first. When the secretary then builds an invoice for a marked patient, the form shows the gross total, the staff discount line and the net total. With the Exams rule above, a 25 000 FCFA exam showed a staff discount of 3 750 FCFA.

> Important: Rates are applied to every staff member without a decision from you. Keep the list short and review it when someone leaves.

## Stock adjustment requests

Quantities of the pharmacy stock only change through decisions you take. A request reaches you in two ways: a secretary asks for a restock, or the stock controller counts the shelves and finds a gap.

Open [[Stock management]] in the menu, then [[Adjustment requests]]. The list opens on the requests that are pending.

![All requests, with the outcome of each](figures/adjust-all.png)

Use the filter {1} to switch between Pending, Approved, Refused and Cancelled, or to see all of them. Each row shows the product, the request type, the quantity, the reason and the requester.

| Request type | Quantity column | Where it comes from |
|---|---|---|
| Restock | +50 means 50 units to add | A secretary, with a reason |
| Correction | = 215 means the stock must become 215 | The stock controller, after a count |

On a correction the product cell gives three figures: the counted quantity, the stock the system held when the count was made, and the current stock. Read all three before you decide. The gap was computed at the moment of the count, so sales made since may have changed the current stock.

### Approving

1. Select [[Approve]] on the row.
2. Read the browser message "Approve this request? Stock will change immediately." and confirm.

The page answers "Request approved: stock updated." and the row shows the outcome {2}: the stock before and after. On a correction of Honey the stock went from 218 to 215, and on a correction of Efferalgan from 0 to 40.

### Refusing

1. Select [[Refuse]] on the row.
2. Write the reason in [[Decision reason]]. It is required, and the stock controller or the secretary reads it.
3. Select [[Refuse]] in the form.

The refused row keeps your reason {3}. The stock does not change. After a refusal the controller counts again, and a new count of the same product replaces any count request still pending for it.

> Caution: Approving a correction is a decision about the truth of a physical count. When the gap is large, refuse with the reason "recount" instead of correcting the system to a figure nobody has checked twice.

### How often products must be counted

The stock controller counts the shelves. You do not count, but you decide the rhythm. Open [[Stock count]] in the same menu group: you see the tabs Frequency and History.

![The count frequency and the state of each product](figures/count-frequency.png)

The field {1} holds the number of days allowed between two counts, from 1 to 365, and [[Save the frequency]] {2} stores it. The tiles count the products never counted, overdue or up to date. The box {3} limits the table to the products that need attention. A value outside the range is refused in red and the button stays grey. The History tab lists the validated counts with their gaps.

The History tab also shows a card **My adjustment requests**: the correction requests that counts produced, with their number, product, outcome (Pending, Approved, Refused, Replaced by a more recent count or Cancelled) and, for a refusal, your reason. In the detail of a validated count, each gap also shows the outcome of its request.

The Reports screen reports the products never counted and the ones overdue (see the chapter on the daily check).

## The cash register

The cash register compares, for each period, what the system recorded with what the secretary counted. You start it once, you read the closings, you decide the adjustments, and you manage the payment modes. All of it is on one screen: [[Cash closings]].

### Starting the register

Until the register is started, the secretary's Cash closing screen shows "Till not set up". The start card appears at the top of your Cash closings screen, and only while the register has no starting point.

![The confirmation shown before the register is started](figures/admin-start.png "small")

1. Count the notes and coins in the till.
2. Type the amount in [[Starting cash float (cash)]] {1}, without thousands separators.
3. Select [[Initialize the cash register]]. A yellow message repeats the amount and warns that the value can never be changed afterwards.
4. Select [[Confirm initialization]].

From that moment the system counts every payment and withdrawal. Money recorded before is never part of a closing. In the demonstration installation the register is already started, so the card no longer appears.

> Important: The starting float cannot be corrected. Count it twice and do it when nobody is selling.

### Adjustment requests from the secretary

A saved closing cannot be edited. When the secretary finds an error afterwards, the secretary sends an adjustment request from the result screen, as the second guide for the secretary explains. The request waits in the top card of your screen.

![Pending corrections, filters and the list of closings](figures/closures-top.png)

Each request names the closing, the payment mode, the amount (for example 1 000 FCFA less), the reason and the time. Read the reason, then select [[Approve]] {2} or [[Reject]] {3}. Both act at once: there is no confirmation and no field for a reason, so the answer "Correction approved." or "Correction rejected." is your only proof on screen.

An approved adjustment does not change the saved closing. It is counted in the next period as an entry (plus) or an exit (minus), and the next closing lists it under Adjustments applied to this period. The secretary receives a notification with your decision ("Your cash adjustment (...) was approved." or "Your cash adjustment (...) was refused.").

> Note: You and the promoter receive a notification when a secretary sends an adjustment request. A request still undecided after the waiting time set in the daily check settings (see the chapter on reports) also appears in the daily check as a pending cash adjustment.

### Reading the closings

The Closings card lists the closings of the last 30 days. The filters are From and To, the Closing type {4} (all, declared by the secretary, or not declared, which means closed automatically at 11 pm) and the box {5} that keeps only the closings with a difference. Each row shows the day, the type and the cash difference in words, such as "Difference of 1 000 FCFA short". Several closings can belong to the same day, so the date column also shows the time at which each closing was saved. [[View detail]] {6} gives the period with its start and end times.

![The detail of one closing](figures/closure-detail.png)

The detail gives, for each payment mode, the opening, the entries, the exits, the amount Expected {1}, the amount Counted {2} and the Difference {3}, with the comment the secretary wrote. Below the table are the sales cancelled during the period and the adjustments applied to it. Select [[Close detail]] {4} to hide it.

A closing without a counted amount belongs to an automatic closing: nobody counted, and the opening of the next period is the expected cash. Treat a day that was closed automatically as a day that was not checked.

### Payment modes

At the bottom of the screen the card Payment modes lists the four modes of the register: cash, Orange Money, MTN Mobile Money and other mobile money. The list is fixed: you cannot add a mode.

![The four payment modes](figures/closure-modes.png)

For each mode you can change the label {1}, the order {2} and the Active box {3}, then select [[Save]] {4} on the same row. The page answers, for example, "Mode Autre mobile saved." The label of the mode is the name the secretary reads, but the code in brackets on the left never changes.

An inactive mode disappears from the secretary's count: after the mode "Other mobile money" was made inactive, the Cash closing screen of the secretary no longer showed it. Cash cannot be made inactive, because it is the only mode counted physically. Switch a mode off only when the centre no longer uses it, and switch it back on as soon as it is used again.

## Reports and the daily check

[[Reports]] answers two questions: what is abnormal, and how is the activity going. It is read-only except for the two thresholds at the bottom of the page.

![The period, the daily check and the first cards](figures/reports-top.png)

Choose the period with the buttons {1}: Today, 7 days, 30 days, or Custom dates {2}, which opens two date fields and the button Apply. The line under the buttons repeats the period shown. [[Export as PDF]] {3} prepares a PDF of the same period.

### The daily check

The framed box {4} at the top is the list of points to look at, with the badge To watch when the list is not empty. Each point has a label, a type, the date it was first seen and the mention Current state when it is a situation that lasts. The button [[Open the screen]] {5} opens the screen that deals with the point, when your account may open it.

| Type of point | What it means |
|---|---|
| Cash gap, Missing comment | A closing with a difference, or a difference without a comment |
| Automatic closure | A day closed at 11 pm without a count |
| Cancelled sales | More sales cancelled in one day than the threshold |
| Price differs from catalogue | An invoice entered offline at another price |
| Other release | A production release that is neither a sale nor a sample |
| Batch out of tolerance, Batch too long, Shipped versus received gap | Production anomalies |
| Never counted, Count overdue | Pharmacy products that were not counted in time |
| Pending adjustment | A stock request waiting too long for your decision |
| Pending cash adjustment | A cash adjustment request from a secretary waiting too long for a decision |
| Input below threshold | A production input whose stock fell under its alert threshold |

The label of each point is written in the language of the interface, for example "Adjustment request no. 321 pending for 4 days". A note under the list says how many days were recomputed when the server had to rebuild days without a nightly record.

### The cards

Under the daily check the cards are grouped in four blocks. Every card states its period and its source at the bottom.

| Block | What it shows |
|---|---|
| Money | Collected amount by mode, cash gaps, withdrawals and cancelled sales, discounts granted, and the amount collected per secretary and per worked day |
| Products | Sold against received quantities, the stock count state, out of stock and low stock products |
| Production | Batch status, bottles produced, released and shipped, shortfall and cost price |
| Growth | New patients, consultations and sales over three months, week by week |

The stock cards and the production status describe the current state, not the chosen period, and say so. The table at the end, Total sold per product, has a search box and filters, and shows amounts before discounts, so it can differ from the collected figures of the Money block.

> Note: [[Export as PDF]] downloads a file named rapports_ followed by the first and the last day of the period, for example rapports_2026-10-01_2026-10-26.pdf. It holds the daily check and the cards of the period, under the header of the centre.

### The two thresholds

At the bottom of the page, only you see the card Daily check settings.

![The two thresholds of the daily check](figures/reports-settings.png)

[[Threshold of cancelled sales in a day]] {1} is a whole number from 1 to 1000: a point is reported when a day has more cancelled sales than this number. In the demonstration installation it is 3. [[Waiting time of adjustment requests (days)]] {2} is a whole number from 1 to 365: a stock request or a cash adjustment request pending for longer than this is reported. It is also 3. Select [[Save the settings]] {3}; the page answers "Settings saved." A value outside the range is refused with a red message and nothing is saved. The new values were still there after the page was reloaded.

## Other settings that only you can change

### Production tracking

In the menu group Production, [[Production tracking]] shows the status of the batches and the anomalies. At the bottom, the card Tracking settings is yours.

[[Loss tolerance (%)]] is the share of bottles that may be missing at shipping before the batch is flagged as out of tolerance, between 0 and 100. [[Days before the batch-too-long alert]] is the number of days a batch may stay in production. Select [[Save settings]]; the page answers "Settings saved." The tolerance applies to the next shipped batches, and a batch already shipped keeps the tolerance it was shipped with. The browser refuses a tolerance above 100.

### System Configuration

[[System Configuration]] has four sections, each folded or unfolded by selecting its title.

The first, Organisation identity and document header, holds the logos, the name and the contact lines that are printed on invoices, prescriptions and reports, and the legal numbers (NIU and RCCM). Edit the fields and select [[Save the organisation settings]]. A message confirms "Structure settings saved successfully." The legal name is required.

Inside the same section the Ticket print token is the secret that the receipt printer bridge uses. Do not regenerate it without reason. A regeneration is possible only after ticking the confirmation box, and the printers stop until the new token is copied into the configuration file of the bridge on every workstation. A new token is meant to be generated only at installation.

The second section is Exam Pricing, described in the first guide. The third, Prayer Book Types, is a read-only list of codes and labels. The fourth, General Settings & Maintenance, holds one card, Database Backup. It only states that "Backups are handled by the server (see operations manual)." The backups of the database belong to the technical team; nothing on this screen starts or changes a backup.

## Financial Management

[[Financial Management]] is the ledger of money in and out: payments received at the cash desk and withdrawals, both listed with their status. It is the screen to answer "what came in and what went out between two dates".

The three tiles at the top give the income, the expenses and the cash balance of the entries found by the filters. The search box, the category list, the two date fields and the buttons All, Income and Expenses narrow the table. The category list mixes the codes used by the application with older French labels, so a category may appear in two spellings. An invoice released by a discount decision before any payment moved no money and is not listed.

### Recording an entry yourself

[[New Transaction]], at the top right, opens a form for an income or an expense.

![The new expense form](figures/finance-form.png "small")

1. Select the type {1}: Income or Expenses.
2. Type the amount {2}, greater than zero, and check the date {3}.
3. Choose the category {4} and the payment method {5}. The list of categories changes with the type.
4. Describe the entry in [[Description / Reason]] {6}.
5. Select [[Save Transaction]] {7}.

The form opens with a yellow warning: "Attention. This creates a real payment or withdrawal. It counts in the cash closing, like any till operation."

> Caution: An expense recorded here is a real cash withdrawal. It appeared in the secretary's list of withdrawals, and it counts in the next cash closing, where the secretary has not recorded it. An income recorded here is a real payment. Use this form only when the secretary cannot, and tell the secretary at once. A wrong entry is cancelled by a secretary with a written reason, as for any withdrawal.

## Audit and security

[[Audit & Security]] answers "who did what, and when". It has two tabs.

![The action audit, filtered from a date](figures/logs.png)

Action Audit {3} lists the actions of the staff: the user, the type of record, and the action, such as UPDATE, APPROVE, REJECT, REQUEST or SET_STAFF. The decisions of this guide all leave a line there: the discount decisions, the approvals and refusals of stock requests, the rejection or approval of a cash adjustment, the changes of payment modes, of thresholds and of staff discount rules, and the refused closings of the secretary. The list shows the most recent first, twenty lines per page, and the arrows under the table change the page.

The Start date field {1} shows only the entries from that day on. It applies to the tab you are on, so set it again after you change tabs. Connection History {2} lists the sign-ins and sign-outs.

Two limits are worth knowing. The Details column summarises what changed, for example the field with its old and new value; passwords and tokens are never shown. Connection History records the sign-ins, the sign-outs and the failed sign-ins, with the reason of a failure (unknown user name, inactive account or wrong password), which the sign-in screen itself does not give. Creating, changing and deleting a staff account are logged in the Action Audit too.

## Common mistakes

**Approving a discount without reading the amount.** The card shows the full price, and the percentage applies to it. A 100% approval makes the invoice free.

**Leaving a request for the promoter in the pending list.** You cannot decide it. Ask the promoter, or ask the secretary to send it again to you.

**Correcting the stock to a count nobody rechecked.** An approval changes the stock immediately and cannot be undone from the screen.

**Leaving the cash adjustments undecided.** The secretary waits for your answer, and the next period then starts without the correction.

**Starting the register with an estimate.** The starting float can never be changed.

**Recording an income or an expense in Financial Management for a sale the secretary should record.** The entry counts in the cash closing, and the secretary then sees a difference.

**Changing a threshold or a rate and forgetting to save the row.** Each rule row and each settings card has its own Save button.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "The password you entered is incorrect." on a discount card | The password typed is not yours | Retype it. After five failures wait one minute. |
| "An approval must grant a percentage and/or a due date." | You approved without a percentage or a deadline | Choose a percentage or a date. |
| "This request is not addressed to you." | The request was sent to the promoter | Ask the promoter to decide. |
| "Approve this request? Stock will change immediately." | Confirmation of a stock decision | Confirm only after reading the three figures of the row. |
| The refusal form will not send | The decision reason is empty | Write a reason. |
| The Approve button of a stock request answers with an error under the row | The stock changed since the request, or the request was already decided | Reload the list and read the current stock. |
| The Cash closings card shows no start card | The register is already started | Nothing to do. |
| "Enter a whole number from 1 to 1000." under a threshold | The value is outside the range | Type a whole number in the range. |
| The Refuse button of a discount card is grey | A percentage or a deadline is selected | Select Clear my choice, then refuse. |
| "Cannot load the data" with a Retry button | The server could not be reached | Select Retry when the connection is back. |
| The secretary no longer sees a payment mode in the closing | The mode was made inactive | Tick Active again on the Cash closings screen. |

## Glossary {.unnumbered}

Adjustment request
: A request, from a secretary after a cash closing or for a stock quantity, that waits for your decision.

Automatic closing
: A closing made by the system at 11 pm for a day without a manual closing. Nothing is counted on it.

Correction
: A stock request created from a physical count. Its quantity is the value the stock must become.

Daily check
: The framed list at the top of Reports with the points that need attention.

Deadline
: The date until which an invoice may be paid by instalments after an approved request.

Discount request
: A request from a secretary to a manager to lower the price of an invoice, locked until the decision.

Opening float
: The cash in the till when the register is started. It is set once and never changes.

Payment mode
: One of the four ways of paying, each with its own line in the closing.

Staff member
: A patient who is marked as staff and receives the automatic staff discount.

Tolerance
: The share of bottles that may be missing at shipping before a production batch is flagged.
