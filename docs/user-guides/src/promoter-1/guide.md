---
title: Reports and daily control
role: Promoter
subtitle: Reading the Reports page, the daily check of anomalies and its notification, the figures of money, products, production and growth, and the PDF export.
version: 26 October 2026
output: promoter-1-reports-daily-control
---

## Before you start {.unnumbered}

This is the first guide for the promoter. It covers the Reports screen, which answers two questions: what is abnormal at the centre, and how the activity is going. The second guide covers the approvals that wait for your decision. The administrator guide on oversight describes the same Reports page from the administrator side, with the settings that only the administrator can change.

The screenshots come from a demonstration installation. Your screens show the real figures of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures. The names and amounts in the figures are test data.

### What the promoter can do on this screen

You read. The Reports page is read-only for you: you cannot enter a figure, correct a closing, approve a stock request or change a threshold. You choose the period, read the cards, search the table of sold products, follow the links of the daily check, and export a PDF.

Two thresholds of the daily check, the number of cancelled sales in a day and the waiting time of stock requests, belong to the administrator. The card that sets them does not appear on your page.

### Your menu

After you sign in, the application opens on the Overview page, then your menu lists the screens of your role.

![The promoter menu and the notification bell](figures/home.png)

[[Reports]] {1} is the screen of this guide. The bell {2} holds the notifications, among them the nightly daily check. [[Pending discount requests]] {4} is the subject of the second guide.

> Caution: The Overview page that opens first shows the label "Indisponible" in the money tiles {3} and offers quick actions such as Manage Staff and Receive Payment. Those tiles are built for the administrator and the server refuses them to the promoter. They do not describe a fault of the centre. Use Reports for every figure.

> Note: The connection indicator at the top reads "Offline (your entries are saved)" even while the server answers. Reports needs the server and does not use the indicator. Judge the connection by whether the page loads.

### Interface language

The language switch sits at the top right, next to the bell. Select **EN** to work in English. Some labels come from the server and stay in French, for example the sentence of an anomaly ("Demande d'ajustement n. 321 en attente depuis 4 jours") and the name of the source at the foot of each card. This guide quotes them as they appear.

## Choosing the period

Everything on the page follows one period: the daily check, the cards and the table of sold products. Dates are the local dates of the centre.

![The period buttons, the export button and the daily check](figures/reports-top.png)

1. Select [[Reports]] in the menu.
2. Select one of the buttons {1}: Today, 7 days or 30 days. The selected button is filled. The line under the buttons repeats the period, for example "Figures from 20 Oct 2026 to 26 Oct 2026".
3. Wait for the cards to refresh. A short line "refreshing" appears above the cards while the figures reload.

The period of 7 days counts today and the six days before. The period of 30 days counts today and the twenty-nine days before. The page opens on Today.

### Custom dates

Select [[Custom dates]] {2} when you need another range, for example a calendar week or a month.

![The two date fields and the Apply button](figures/custom-dates.png "small")

1. Choose the first day in [[From]] {1}.
2. Choose the last day in [[To]] {2}.
3. Select [[Apply]] {3}.

The page refuses a range whose end date is before the start date and writes "The end date is before the start date." under the buttons. Nothing is loaded until the range is correct. Selecting Today, 7 days or 30 days again closes the two fields.

## The daily check

The framed box {4} at the top of the page, under the period, is the daily check. It lists the points that deserve a look, in words, so that you do not have to search the cards for what is wrong.

When the list is not empty, the badge {5} reads "To watch". When nothing is wrong over the period, the box says so and the badge changes. The check never needs a decision from you: it is a reading aid.

### Reading one point

Each point is a row with a sentence, a type, and a few marks.

![One point of the daily check and its marks](figures/control-item.png)

The coloured badge {1} gives the type of the point. The mark {2} gives the day the point was first seen. The mark {3} appears only when the nightly notification already announced this point: "already reported on 25 Oct 2026". The badge {4}, "Current state", marks a situation that lasts, such as a product never counted, as opposed to an event of one day, such as a cash gap.

The types you can meet are the following.

| Type of point | What it means |
|---|---|
| Cash gap, Missing comment | A cash closing with a difference, or a difference without a comment from the secretary |
| Automatic closure | A day closed by the system at 11 pm because nobody closed it |
| Cancelled sales | More sales cancelled in one day than the threshold set by the administrator |
| Price differs from catalogue | A sale entered offline at a price other than the catalogue price |
| Other release | A production release that is neither a sale nor a sample |
| Batch out of tolerance, Batch too long, Shipped versus received gap | Anomalies of the production batches |
| Never counted, Count overdue | Pharmacy products that were not counted, or not counted in time |
| Pending adjustment | A stock request that has waited longer than the limit for the administrator |

Some sentences arrive in French from the server. The type badge next to the sentence is always in English, so read the badge for the meaning.

### The "Open the screen" button

When the point has a screen that deals with it, the button [[Open the screen]] {6} appears at the end of the row. In the demonstration installation the button of a cash gap opened Cash closings, and the button of the products never counted opened Stock count.

The button appears only when your account may open the screen. The pending stock request of the figure has no button: Adjustment requests belong to the administrator, and a direct visit to that address opens a page titled "Accès Interdit" (access forbidden), in French. When a point has no button, tell the administrator about it.

> Note: A point with the type Pending adjustment is a question for the administrator, and a point with the type Cash gap is one you can follow yourself in Cash closings, where the closing detail and the comment of the secretary are written.

### Days without an evening record

Under the list, a grey line may say "29 day(s) without an evening record were recomputed." The nightly record, described in the next chapter, exists only from the day the check was put in service. For earlier days, and for any day the night run missed, the page recomputes the points from the data as they stand now. A recomputed day is shown with the badge "Recomputed" on its point. Treat these days as a good estimate and not as a frozen record.

If more than about a month of the period has neither a record nor a recomputation, a yellow note reads "N day(s) of the period are not checked (no snapshot)", with the range. Choose a shorter period to see those days.

## The nightly check and its notification

The page shows the points live. In addition, the server runs the check once every night, at 23:30 in the time of the centre. The run stores the list of points of the day, and it can notify you.

### What triggers a notification

The notification goes to the promoter and to every active administrator. It is sent only when the run finds at least one new point since the previous night. A night with no anomaly sends nothing. A night where all the points were already announced sends nothing either. Points that stay open are announced once, then repeated in one reminder every seven days for as long as one of them is still open.

The message appears in the bell, for example "Daily check of 2026-10-25: 2 new point(s), 0 still open". A short message at the top right of the screen also tells you when new notifications arrive. The date in the message is written year, month, day.

![The nightly notification in the bell](figures/bell.png "small")

1. Select the bell {1}.
2. Read the entry {2}. The first number is the new points, the second the points that were already open.
3. Select the entry. It is marked as read and the Reports page opens.

The notification does not list the points. Open Reports and read the daily check, where the first column of marks tells you which points are new.

> Important: The bell shows many other notifications, such as cash closing anomalies and lab alerts. The nightly check is a summary of the day and does not replace them.

### How a point stays or leaves the list

A point has a stable identity: the same cash gap, the same batch, the same pending request. The live list shows the points that exist now. A point whose cause has been dealt with, such as a stock request that the administrator decided, is therefore expected to leave the list of the following days, while past days keep their stored list. This guide did not play that case through to the end.

On the evening of the demonstration, the stored list contained two points, the pending request and the products never counted. When the page was opened the next morning, the same two points carried the mark "already reported on 25 Oct 2026" while a cash gap found that morning carried none. That mark is the quickest way to tell what you have already been told from what is new.

## The cards

Under the daily check the cards are grouped in four blocks: Money, Products, Production and Growth. Each card is one indicator. Every card states at its foot the period it covers and the source of its figures. A card that describes the situation now, and not the chosen period, carries a blue badge "Current state as of" with the time, and its foot says "current state, not the chosen period".

### Money

![The five cards of the Money block](figures/money.png)

**Collected over the period** {1} gives the total collected, then the total for each payment mode: cash, Orange Money, MTN Mobile Money and other mobile money. It counts the entries of the cash closings, including the payments of sales that were cancelled later and the withdrawals that were returned. A line Unclassified holds payments whose mode is not known. In the figure it is 0.

**Cash gaps** {2} adds the gaps of the closings of the period, in absolute value, so that a shortage and a surplus never cancel each other. Under the total, each closing is listed with its day, its type (manual or automatic) and its gap, with a minus sign for a shortage.

**Withdrawals and cancelled sales** {3} gives the amount and the number of withdrawals with their categories, then the cancelled sales with their count, the invoice total, the amount returned, and one line per sale with the account that cancelled it and the written reason.

**Discounts granted** {4} has two parts. The approved manual discounts are the requests that you and the administrator decided, counted by decision date. The staff share is the automatic discount for staff members, counted by payment date. The two are shown side by side and not added together.

**Collected per secretary** {5} divides what each account collected by the days the account really collected, and not by the days of the period. A secretary who worked two days is judged on two days. The line "Of which sales cancelled later" shows how much of the collected amount was returned afterwards.

> Caution: The card does not compare secretaries by week, and a low figure per day does not prove a fault: a secretary may have worked only a short day. Use it to ask a question, then open Cash closings and the sale list.

### Products

![The three cards of the Products block](figures/products.png)

**Products sold versus received** {1} compares three numbers: the quantities sold over the period in active sales, the quantities received over the period, and the system stock now. Received counts the validated receipts and the approved restockings, and the card shows the split between the two. Production lots enter the stock through receipts, so they are not added a second time. A sale that is cancelled, refunded or still waiting for a discount decision does not count as sold.

**Stock count** {2} gives the state of the weekly counting of the pharmacy: products never counted, overdue, and up to date, with the frequency in days and the number of pending adjustment requests. Under the numbers each product that needs attention is listed with its state.

**Out of stock and low stock** {3} lists the products whose quantity is lower than or equal to their alert threshold, with the stock and the threshold. These two cards describe the situation now.

### Production

![The three cards of the Production block](figures/production.png)

**Batch status** {1} counts the batches in each state (draft, in production, finished, shipped, cancelled) and the batches that stayed too long, with the limit in days. It describes the situation now.

**Bottles produced, released and shipped** {2} counts, over the period, the good bottles produced by the batches finished in the period, the sample releases, the other releases and the bottles shipped.

**Shortfall and cost price** {3} gives the number of batches out of tolerance, which is a state of now, and the average cost per good bottle of the batches shipped in the period. The value is "None" when no batch was shipped in the period. In the demonstration installation the production block shows only zeros because no batch was made.

### Growth

![The two curves of the Growth block with their weekly tables](figures/growth.png)

The two curves {1} {3} cover the last three months week by week, whatever period you chose above. The current week is not finished, so its last segment is dashed. The left card counts new patients, medical consultations and spiritual consultations. The right card shows sales, with the previous three months as a second line to compare.

Select [[See the weekly figures]] {2} to open the same numbers as a table. The table gives the exact value of a week, which a curve cannot.

## Total sold per product

The last block of the page is a table of what was sold, line by line, over the chosen period. It answers a question such as "how many bottles of honey did we sell this month, and for how much".

![The filters and the table of sold products](figures/table.png)

The amounts are the amounts of the invoice lines before any discount. The sentence at the foot of the card says so: the table may differ from the amounts collected in the Money block, which are net of discounts and count payments, not invoice lines.

1. Type part of a name in [[Search a product]] {1}. The table filters about a third of a second after you stop typing.
2. Choose a [[Type]] {2}: Medicine, Exam, Consultation or Service. The page opens on Medicine.
3. Type a category in [[Category]] {3} to keep one category. The category must be written in full, as it appears in the table: "Naturel" finds the products of that category, while "nat" and "naturel" find none. The letter case must match too.
4. Choose a sorting in [[Sort by]] {4}: amount or quantity, highest or lowest first, or name from A to Z.
5. Use [[Previous]] and [[Next]] {5} to move through the pages. Each page holds fifty lines, and the line under the table says which lines are shown, for example "1 to 3 of 3".

Only active sales count. A cancelled or refunded sale and a sale that waits for a discount decision are left out. A sale belongs to the day of its payment. For the types Consultation and Service the table shows one line for the type, such as Service with a quantity of 4, because these lines have no product name.

## Exporting the page as a PDF

[[Export as PDF]] {3} on the period card prepares a PDF of the page for the period shown. The file is meant to be printed or sent: it carries the header of the centre, the daily check, the figures of the cards and the table of sold products.

1. Choose the period.
2. Select [[Export as PDF]]. The button shows a waiting label while the server prepares the file.
3. Open the file that the browser downloads. Its name is "rapports_" followed by the two dates, for example rapports_2026-10-20_2026-10-26.pdf.

If the server cannot prepare the file, the page writes a red sentence next to the button: "Could not generate the PDF. Please try again."

> Caution: During the preparation of this guide, the sentence above appeared every time in the test browser, although the server answered normally and returned a valid PDF when it was asked directly. The cause was on the computer and not in the centre's server: a download manager installed on that computer intercepted the download request and answered it itself, with an empty reply, before the page could receive the file. If you see the sentence, pause or close the download manager of your computer, or add the address of the application to its exclusions, then try again. If the sentence stays, tell the technical team.

## What you cannot do here

Reports is a reading page. The following actions exist in the application but not on your side:

| You want to | Who can |
|---|---|
| Change the number of cancelled sales that triggers a point, or the waiting time of stock requests | The administrator, in the card Daily check settings at the foot of the page |
| Approve or refuse a stock request | The administrator |
| Decide an adjustment request after a cash closing | The administrator or the promoter, in Cash closings |
| Change the tolerance of the production batches | The administrator, in Production tracking |
| Record an income or an expense in the ledger | The administrator |
| Read the action log | The administrator |

When you type the address of one of these screens directly, the application opens the page "Accès Interdit". Nothing is changed.

## Common mistakes

**Reading the Overview page as the figures of the centre.** The money tiles of that page are blank for the promoter and show "Indisponible". Use Reports.

**Comparing the table of sold products with the Money block.** The table is before discounts and counts invoice lines, the Money block counts payments received. A difference is normal.

**Taking a card of the current state for the figures of the period.** The cards for the stock count, the low stock, the batch status and the batches out of tolerance show the situation now. Their foot says "current state, not the chosen period" and the blue badge gives the time.

**Waiting for a notification when nothing is new.** The nightly run sends nothing when no new point appeared and sends one reminder per week for the points that stay open. A quiet bell does not mean an empty list: open Reports.

**Concluding too fast from the figure per worked day.** The division is by the days the account collected, and a short day gives a small figure.

**Typing half a category.** The category filter needs the whole word, with the same capital letters as the table.

**Reading a recomputed day as a frozen record.** A day marked "Recomputed" was calculated from the data now, so a later correction can change it.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Could not generate the PDF. Please try again." | The export failed on the way to your computer | Pause the download manager of the computer, then try again. If it stays, tell the technical team. |
| "The end date is before the start date." | The custom range is the wrong way round | Swap the two dates and select Apply. |
| A red message with a Retry button in the daily check or in the table | The server did not answer | Select the button. If it fails again, check the connection and tell the administrator. |
| "Indisponible" in the money tiles of the Overview page | The tiles are for the administrator | Open Reports. |
| A point of the daily check has no Open the screen button | The screen belongs to another role | Tell the administrator about the point. |
| The page "Accès Interdit" opens after you typed an address | The screen is not part of your role | Use the menu on the left. |
| A card shows a figure with no period or source | This should not happen | Note the card and tell the technical team. |
| No notification arrived this morning | Nothing new was found, or the night run did not run | Open Reports and read the daily check. If the day before the last is missing, tell the technical team. |

## Glossary {.unnumbered}

Anomaly
: A fact that deserves attention: a cash gap, a closing without a count, a batch out of tolerance, a product never counted, a stock request that waits too long.

Current state
: A figure that describes the situation now and not the chosen period. Its card says so and gives the time.

Daily check
: The framed list at the top of Reports. It shows the points of the chosen period, in words, with the day each one was first seen.

Evening record
: The list of points stored by the nightly run at 23:30. It is the reference for a past day.

Notification
: A message in the bell. The nightly check sends one only when a new point appeared, or as a weekly reminder.

Period
: The range of local days shown by the page. Today, 7 days, 30 days or custom dates.

Recomputed
: Said of a day without an evening record, whose points were calculated from the data as they stand now.

Source
: The name of the part of the application that provides the figures of a card, written at its foot.

Worked day
: A day on which an account collected at least one payment. The card Collected per secretary divides by these days.
