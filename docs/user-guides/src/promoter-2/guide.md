---
title: Approvals and follow-up
role: Promoter
subtitle: Deciding discount requests and cash adjustments, setting the staff discount rules, reading the notifications, and following the laboratory stock, the production and the toxicology programme.
version: 26 October 2026
output: promoter-2-approvals-follow-up
---

## Before you start {.unnumbered}

This is the second guide for the promoter. The first one covers the Reports screen and the daily check. This one covers the decisions that wait for you and the screens you use to follow the centre between two reports. The administrator guide on oversight describes several of the same screens from the administrator side. This guide is written from your seat and says where you can do less, or something different.

The screenshots come from a demonstration installation. Your screens show the real data of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures. The people and amounts in the figures are test data.

### Your menu

After you sign in, the application opens on the Overview page and the menu lists the screens of your role.

![The promoter menu, the bell and the account icon](figures/home.png)

Two entries are decisions: [[Pending discount requests]] {1} and [[Cash closings]] {2}. [[Staff discounts]] {3} holds a setting. The others are follow-up screens: [[Stock count]] {4}, [[Lab stock]] {5} and [[Production]] {6}. [[Discount history]], [[Reports]] and Toxicology Monitoring complete the menu. The bell {7} holds your notifications and the account icon {8} opens your profile and password.

The Overview page itself is built for the administrator. Its money tiles read "Indisponible" for you and the quick actions lead to screens you may not open. Only the Bed Occupancy tile, which counts the hospitalised patients, gives you a figure there. The guide on reports explains why, and it also explains the connection indicator that reads "Offline (your entries are saved)" even while the server answers.

### What you can do differently from the administrator

You and the administrator share the discount decisions and the staff discount rules. Both of you decide on cash adjustments. Your rights are narrower elsewhere, and a few are wider.

| Subject | Promoter | Administrator |
|---|---|---|
| Discount requests | Decides the requests addressed to the promoter | Decides the requests addressed to the administrator |
| Cash closings | Reads the closings and decides adjustments | Same, and also starts the register and manages the payment modes |
| Stock adjustment requests, Financial Management, Users, Patients, Audit & Security, System Configuration | Not in the menu, and the address is refused | Full access |
| Stock count | Reads the frequency and the history | Also sets the frequency in days |
| Reports | Reads everything | Also sets the two thresholds |
| Production | Reads batches, inputs and tracking | Also sets the loss tolerance and the delay alert |
| Lab stock | Reads, handles orders, enters receipts | Same, and also cancels a receipt |
| Toxicology | Reads the list and can discharge a patient | Same, and also exports the dossier as a PDF |

A page that your role may not open sends you to a "Forbidden" screen. It is not a fault of the application.

## Discount requests

A secretary cannot change the price of a catalogue item. When a patient asks for a lower price, the secretary sends a discount request to the administrator or to you, and the invoice stays locked until that person decides. You only see the requests addressed to you.

### Deciding a request

Select [[Pending discount requests]] in the menu. Each request is a card with the invoice amount at the top, the patient, a short summary of the lines and the name of the secretary.

![One request, ready to be decided](figures/discount-card.png "small")

1. Read the card. The amount is the full price before any reduction.
2. To grant a percentage, select one of the four buttons {1}: 10%, 20%, 50% or 100%. No other percentage exists.
3. To grant time to pay instead of a reduction, or as well as one, choose a date in [[Deadline (installment plan)]] {2}.
4. Type your own password in [[Confirm with your password]] {3}. The password proves that the decision is yours.
5. Select [[Approve]] {4}, or [[Refuse]] {5}.

The card disappears and the secretary is notified. Four decisions were taken on invoices of 25 000 FCFA, and the discount history recorded them as follows.

| Decision | Result in the history |
|---|---|
| Approved at 50% | Reduced amount of 12 500 FCFA |
| Approved with a deadline of 20 November 2026 and no percentage | Approved, with no reduced amount |
| Refused | Refused, with no reduced amount |
| Refused with 10% selected by mistake | Refused, and the percentage is ignored |

Two checks protect you. A wrong password answers "Mot de passe incorrect." in red under the fields, as the figure shows, and nothing is decided. An approval with no percentage and no deadline answers "Une décision d'approbation doit accorder un pourcentage et/ou une échéance." in French. In both cases the card stays and you can try again.

> Caution: A refusal does not cancel the invoice. It releases the invoice at its full price, and the secretary then collects the money or cancels the invoice. A percentage always applies to the full price. Approving 100% makes the invoice free, so read the amount before you select a button.

> Note: The labels of the answers and the notifications of this chapter are still partly in French, for example "Mot de passe incorrect." and the secretary's entry "Demande de réduction refusée". This guide quotes them as they appear.

### Requests addressed to the administrator

A request sent to the administrator never appears in your list, and you receive no notification for it. During the preparation of this guide four requests were sent, three to the promoter and one to the administrator. Your list showed three and the bell announced three.

You can still see the fourth in the history. If a request stays pending for days, ask the secretary whether it was sent to the administrator, and ask the administrator to decide, or ask the secretary to cancel it and send it to you.

### Reading the history

[[Discount history]] lists every request, whoever it was addressed to. It is read-only.

![The discount history and its indicators](figures/discount-history.png)

The four tiles {1} count the approved, refused and pending requests and give the total amount reduced for the period. The buttons {2} choose This week, This month or Custom, and the date fields set the range. The Status filter {3} narrows the table to one outcome. The column {4} shows the amount reduced, which stays empty when only a deadline was granted. The column Decided by tells you which of the two managers took the decision.

## Staff discounts

The centre grants an automatic reduction to its own staff. The rules and the list of staff members are kept in [[Staff discounts]], which you share with the administrator. You may change them.

![The rules by category and the staff members](figures/staff-rules.png)

A rule belongs to a category of invoice line: Medications, Exams, Consultations, Booklets or Other care. It has a minimum invoice amount {1}, a rate in percent {2} and an Active box {3}. A rule applies when the invoice total reaches the minimum. In the demonstration data the Exams rule gives 15% from 2 000 FCFA and the Medications rule gives 10% from 3 000 FCFA. The three other categories are switched off.

To change a rule:

1. Edit the minimum or the rate on the row of the category.
2. Tick or untick [[Active]] {3}.
3. Select [[Save]] {4} on the same row. The row answers "Rule saved."

Each row has its own Save button, and it saves that row only. A rate must be a whole number from 1 to 100. A rate of 0 is refused with the message "The rate must be an integer between 1 and 100." under the row, and nothing is saved.

To mark a person as staff:

1. Type at least two letters of the name or code in [[Search a patient]] {5}.
2. Select [[Mark as staff]] {6} on the right row. The person appears in the list of staff members below.
3. To withdraw the reduction, select [[Remove]] on the same person.

The person must exist as a patient first. The rules apply to every staff member without a decision from you, and a percentage approved on a discount request replaces the automatic staff discount of that invoice.

> Important: Keep the list of staff members short and review it when someone leaves. Changing a rate changes the price of every later invoice for those people.

## Cash adjustments

The secretary closes the cash register each day. A saved closing can never be edited. When the secretary finds an error afterwards, the secretary sends an adjustment request from the result screen of the closing, and you or the administrator decide it. Starting the register and managing the payment modes belong to the administrator only, so your screen has neither.

Select [[Cash closings]] in the menu. The page opens on the pending corrections, then the list of closings.

![Pending corrections at the top of the Cash closings screen](figures/closures-top.png)

The card [[Pending corrections]] {1} lists one entry per request. Each entry gives the closing number, the payment mode, the amount more or less, the reason written by the secretary and the time of the request.

1. Read the reason.
2. Select [[Approve]] {2} to accept the correction, or [[Reject]] {3} to refuse it.

Both buttons act at once. There is no confirmation and no field for a reason. The page answers "Correction approved." or "Correction rejected.", and the entry leaves the list.

An approved correction does not change the saved closing. It is counted in the next period as an entry (plus) or an exit (minus), and the next closing lists it under Adjustments applied to this period. A rejected one changes nothing. The page does not tell the secretary what you decided, so tell the secretary.

> Caution: You are not notified when a secretary sends an adjustment request. Two requests were sent while this guide was prepared and the bell stayed silent. Open Cash closings every day. The daily check of the reports does not list cash requests either.

> Note: The subtitle of this screen says "Read only." That sentence is wrong for the pending corrections, which you decide. It is right for the list of closings.

### Reading the closings

Under the corrections, the card Closings lists the closings of the last 30 days. You can filter by dates, by closing type (declared by the secretary, or not declared, which means closed automatically at 11 pm) and by the box that keeps only the closings with a difference. Each row shows the day, the type and the cash difference in words, such as "Difference of 1 000 FCFA short". Several closings can belong to the same day and the list shows the day only, not the time.

Select [[View detail]] on a row to see, for each payment mode, the opening, the entries, the exits, the amount expected, the amount counted and the difference, with the comment of the secretary. A closing without a counted amount is an automatic closing: nobody counted. Treat a day closed automatically as a day that was not checked.

## Notifications

The bell at the top right of every screen counts what is new for you.

![The bell and the list of notifications](figures/bell.png "small")

Select the bell {1} and read the entries from the top, most recent first. Selecting an entry marks it as read and opens the screen that deals with it. A short message also appears at the top right when new entries arrive, and closes by itself. The entries below were seen during the preparation of this guide, and each was selected once to check where it leads.

| Entry | What it means | What happens when you select it | What you do |
|---|---|---|---|
| "Grace Mbarga demande une réduction (25000 FCFA)" {3} | A secretary asked you for a discount | Opens Pending discount requests | Decide the request |
| "Cash closing of 2026-10-26: cash expected ..., counted ..., No difference" | A closing was saved and matches | Opens Cash closings | Nothing, unless you want to read it |
| "Anomaly: Cash closing of 2026-10-26: ..., Difference of 1000.00 short" | A closing was saved with a difference | Opens Cash closings | Open the detail and read the comment |
| "Daily check of 2026-10-25: 2 new point(s), 0 still open" | The nightly check found points to look at | Opens Reports | Read the daily check |
| "Lab: produis test almost out" {2} | The technician reported a low product | Opens To order | Order the product |
| "Lab: produis test (lot 1) expires in 5 day(s)" | A lot is close to its expiry date | Opens Lab alerts | Check the lot and use it first |

When the technician reports a product as out, the entry reads "out" instead of "almost out". The application also has entries for the weekly count reminder of the laboratory and for a product that was received. They did not appear during the preparation of this guide.

Some entries are meant for the administrator or for the stock controller, for example stock adjustment requests and price differences. If one reaches you, selecting it does not lead anywhere, because you cannot open those screens.

> Caution: Opening the screen is not a decision. An entry that you read stays read even if the request is still waiting. The list of Pending discount requests and of Pending corrections is the real list of what is left to do.

## Following the laboratory stock

The laboratory has its own stock of reagents and consumables. The technician counts and reports. The stock controller receives deliveries. You follow the stock, you decide what is ordered, and you can enter a delivery yourself. Open [[Lab stock]] in the menu to unfold six screens: Lab products, To order, Lab receipts, Lab alerts, Lab history and Lab expenses.

On [[Lab products]] you read the stock, the alert threshold and the date of the last count of each product. You cannot add or edit a product, and the Report button of the technician is not on your screen.

### Alerts

[[Lab alerts]] gathers three things.

![Weekly count, low stock and upcoming expiries](figures/lab-alerts.png "small")

The card Weekly count {1} says when the last count was made and whether one is due. The card Low stock {2} lists the products under their threshold. The card Upcoming expiries {3} lists the lots with the number of days left. You only read this page.

### Ordering a product

When the technician reports a product as almost out or out, a line appears in [[To order]] with the status To order, and you receive the bell entry shown earlier.

1. Select [[To order]] in the menu. The list opens on the open requests.
2. On the row of the product, select [[Mark as ordered]].
3. Choose the expected delivery date in [[Expected date]] {1}. A date in the past is refused with the message "Value must be 26/10/2026 or later", where the date is today.
4. Select [[Save]] {2}. The page answers "Order saved." and the status becomes Ordered.

![The date of the order](figures/lab-order.png "small")

Select [[Change date]] on an ordered request to change the date. [[Cancel request]] asks for a reason and closes the request. Use the Status filter to read the requests that are ordered, received or cancelled.

### Entering a delivery

When the goods arrive you or the stock controller enter the supplier invoice. Select [[Lab receipts]], then [[New receipt]].

![The receipt form with one line](figures/lab-receipt.png)

1. Type the invoice number {1} and the supplier {2}. The delivery date is today by default.
2. Select [[Add a product]] {3}, search the product and select it. A line appears.
3. On the line, type the quantity ordered and the quantity received, the lot number, the expiry date and the unit price.
4. Tick the box {4} of the line to confirm that you checked the delivery. The total of the invoice updates under the table.
5. Select [[Confirm receipt]] {5}.

The page answers "Receipt saved." and the list shows the invoice as Valid with your name in Entered by. In the demonstration data a delivery of 50 units entered this way moved the stock of the product from 75 to 125, closed the open order of that product as Received, and added 50,000 FCFA to the laboratory expenses. The button stays grey while a line is incomplete, and a red sentence under the table tells you what is missing: the received quantity, the lot, the expiry date or the unit price.

You cannot cancel a receipt. Only the administrator can, so check the lines before you confirm.

[[Lab history]] lists every movement of stock: receipts, count corrections and cancellations, with the stock after each one. [[Lab expenses]] adds up the valid receipts by month and by supplier for the last twelve months, or for the dates you choose.

## Following the production

[[Production]] unfolds three screens: Production batches, Inputs and purchases, and Tracking and anomalies. The production manager enters everything. For you, all three are read-only: there is no New batch button, no New purchase button, and a batch has no action buttons when you open it.

![Production tracking](figures/production-tracking.png "small")

[[Tracking and anomalies]] shows how many batches are in each status {1}: draft, in production, finished, shipped or cancelled. The tile Anomalies {2} counts the batches to review, and the list of anomalies below it names them. [[Recent batches]] {3} lists the latest batches with a button to open each one. The list of declared outputs at the bottom shows the bottles taken out of a batch without being sold, with the reason.

Batches are listed in [[Production batches]], with filters on status and dates, and the stock of each raw material and every purchase are in [[Inputs and purchases]]. The loss tolerance and the delay after which a batch is reported as too long belong to the administrator.

In the demonstration data one batch, FAB-2026-0001, was created by the production manager and stayed in Draft. A draft is the first status, before production is started.

> Note: The daily check of the reports lists the production anomalies too. Use this screen when you want the whole picture of the batches.

## Toxicology monitoring

The promoter is an observer of the toxicology programme with one action: discharging a patient. Select Toxicology Monitoring in the menu.

![The list of followed patients](figures/toxico-list.png)

The tiles at the top give the active patients, the admissions of the month, the relapse rate and the patients in the first phase. The tabs Active and Discharged switch the list. For each patient the row shows the current phase, the relapses and the psychologist. The buttons are [[Details]] {1}, [[File]] {2} and [[Discharge]] {3}.

Details and File open the dossier of the patient: the toxicology history, with the buttons Discharge and Close the file. Unlike the administrator, you have no button to export the dossier as a PDF. The clinical notes of the doctors are not part of this screen.

### Discharging a patient

Discharge closes the stay of the patient in the programme.

1. Select [[Discharge]] {3} on the row of the patient.
2. Choose the reason: Recovery, Dropout, Exclusion or Other.
3. Write a note if you wish. It is optional.
4. Read the yellow sentence: "The ongoing stay will be closed. The patient can be readmitted later (new stay)."
5. Select [[Confirm discharge]].

The form was opened and read during the preparation of this guide, but no patient was discharged, because every patient in the demonstration data is a test record that other guides use. The steps above come from the form itself.

> Caution: A discharge is a decision about care. Take it with the toxicology manager and the psychologist of the patient, and write the reason in the note.

## Your profile and password

The account icon at the top right opens the form My Account, with two tabs.

![The profile tab](figures/account-profile.png "small")

The tab Profile {1} holds the full name, the e-mail address and the phone number. The user name and the role cannot be changed here. Select [[Save]] {4} after a change. The tab Password {2} changes your password.

![The password tab after a wrong current password](figures/account-password.png "small")

1. Type the current password {1}, then the new one twice {2}{3}.
2. Select [[Save]] {4}.

Three checks were seen. A wrong current password answers "L'ancien mot de passe est incorrect", in French. Two new passwords that differ answer "The new passwords do not match." A new password shorter than 8 characters is stopped by the browser with a message that asks for 8 characters or more.

When the change succeeds, the application signs you out of every session and shows the sign-in page again. Sign in with the new password. The first guide for the administrator describes the same form for the administrator.

> Tip: Your account decides discounts, so choose a password that nobody else knows, and never type it while someone looks at the screen. If you forget it, the administrator can set a new one, and you then change it again yourself.

## Common mistakes

**Approving a discount without reading the amount.** The card shows the full price and the percentage applies to it. A 100% approval makes the invoice free.

**Waiting for a notification of a cash adjustment.** There is none. Open Cash closings each day.

**Rejecting or approving a cash adjustment by habit.** Both buttons act at once and cannot be undone from the screen.

**Leaving a request for the administrator unanswered.** It is not in your list. Ask the administrator, or ask the secretary to send it again to you.

**Typing a rate of 0 to switch a staff rule off.** The rate must be from 1 to 100. Untick Active and save the row.

**Forgetting to save a staff rule row.** Each row has its own Save button.

**Entering a lab delivery with a wrong lot or price.** You cannot cancel a receipt. Ask the administrator.

**Marking an order with a past date.** The date must be today or later.

**Expecting the bell to be the list of what is left to do.** The bell tells you what changed. The lists of pending requests and pending corrections tell you what is left.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Mot de passe incorrect." on a discount card | The password typed is not yours | Retype it. Several failures in a row lock the card for a short while. |
| "Une décision d'approbation doit accorder un pourcentage et/ou une échéance." | You approved without a percentage or a deadline | Choose a percentage or a date. |
| A discount request is missing from your list | It was sent to the administrator | Ask the administrator, or read it in Discount history. |
| "Forbidden" page | Your role may not open that screen | Use the screens of your menu. |
| "No pending correction." | No cash adjustment is waiting | Nothing to do. |
| "The rate must be an integer between 1 and 100." | The rate of a staff rule is outside the range | Type a whole number from 1 to 100. |
| "Value must be 26/10/2026 or later" on an order | The expected date is in the past | Choose today or a later date. |
| The Confirm receipt button stays grey | A line of the receipt is incomplete | Read the red sentence under the table and fill the missing field. |
| The Overview tiles read "Indisponible" | The tiles are built for the administrator | Use Reports for the figures. |
| "L'ancien mot de passe est incorrect" | The current password typed in the form is wrong | Retype it. |
| The page asks you to sign in again after a password change | The change was successful | Sign in with the new password. |

## Glossary {.unnumbered}

Adjustment request
: A request from a secretary after a cash closing that waits for a decision from the promoter or the administrator.

Anomaly
: A closing with a difference between the cash counted and the cash expected, or a production point outside the set limits.

Daily check
: The list of points to look at at the top of Reports. Its guide is the first guide for the promoter.

Deadline
: The date until which an invoice may be paid by instalments after an approved request.

Discount request
: A request from a secretary to a manager to lower the price of an invoice, which stays locked until the decision.

Draft
: The first status of a production batch, before production starts.

Receipt
: The entry of a supplier invoice in the laboratory stock, with the lines delivered.

Staff member
: A patient who is marked as staff and receives the automatic staff discount.
