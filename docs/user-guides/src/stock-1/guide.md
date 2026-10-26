---
title: Receipt control and incidents
role: Stock controller
subtitle: Checking the receipts and damage reports entered by the assistant, correcting or refusing them, entering laboratory deliveries, reading the movements and the alerts, and knowing what the screens do without a connection.
version: 27 October 2026
output: stock-1-receipt-control-incidents
---

## Before you start {.unnumbered}

This guide is for the stock controller of the centre. In Glostone-Care you are the second pair of eyes on the stock. The assistant writes down what arrives and what gets broken, and the figure of a product changes only when you say that the entry is right. You also enter the deliveries of the laboratory stock yourself, and those take effect at once. The weekly physical count has its own guide, and nothing about it is repeated here.

The screenshots come from a demonstration installation. The products, suppliers and quantities in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the stock controller can see and do

The application opens on **To check**, the queue of everything that waits for your decision. There is no separate dashboard. Your menu has two groups.

![The menu of the stock controller](figures/menu.png "small")

The group **Stock management** {1} holds **To check** {2}, the queue of receipts and damage reports, **Movements** {3}, the journal of the pharmacy and natural stock, and **Stock count** {4}, which belongs to the second guide. The group **Lab stock** {5} unfolds five screens: **Lab products**, **To order**, **Lab receipts**, **Lab alerts** and **Lab history**.

You can validate, correct or reject the entries of the assistant. You cannot create a receipt or a damage report for the pharmacy and natural stock, and you cannot cancel one. The list of pharmacy products, the production lots, the receipts and damage reports of the assistant, the patient screens, the laboratory count and the laboratory expenses are closed to you. If you type the address of one of them, the application sends you to a page that says 403 and "Access denied", with a button "Go to my dashboard".

You have no button to request a restock. Restock and correction requests for the pharmacy are written by the secretary and decided by the administrator. In the laboratory, the technician reports a product that is almost out, and the promoter or the toxicology manager places the order. Your part is to receive the goods when they arrive.

### Signing in

Each member of staff has a personal account. Ask the administrator for yours.

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]].
3. Type your password in [[Password]].
4. Select [[Sign in]].

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again. Select **EN** in the language switch at the top right, next to the bell, to work in English. The choice is kept on that computer.

## Checking a receipt

A receipt is the written record of a delivery, entered by the assistant. It reaches you in the **Receipts** tab of **To check**, either for a lot made by the production unit of the centre or for a delivery from a supplier. When the assistant saves a receipt, a notice arrives in your bell, and the stock has not moved. Your decision moves it.

![The queue with a receipt selected](figures/queue.png)

The tab **Receipts** {1} and the tab **Damages** {2} show the number of entries waiting. The list on the left gives the number, the date, the origin and the number of lines of each receipt, and the one you selected {3} is outlined. On the right, the header gives the origin (**Manufactured lot** or **Supplier**), the supplier and the delivery reference for a supplier, the reception date and the author {4}. The table shows each product with the quantity **Expected**, then four boxes {5}: **Good**, **Damaged**, **Lost** and **Defective**. **Total** is their sum. [[Reject]] {6} and [[Validate]] {7} close the entry. [[Refresh]] at the top right reloads the queue.

### Validating a receipt

1. Select the receipt in the list.
2. Compare the table with the goods and the delivery note. The lot number and the expiry date appear under the product name.
3. If the figures are right, select [[Validate]].
4. Answer the question "Confirm validation? Stock will be updated." with OK.

The page answers "Validated: stock has been updated." and the receipt leaves the queue. Only the quantity in **Good** is added to the stock of the product. The damaged, lost and defective units are recorded on the receipt and written in the note of the stock movement, for example "Réception REC-20261026-006 (avaries : endommagé 3)", but they add nothing. For a manufactured lot, the lot passes to the status **Received**. The assistant receives a notice that the receipt was validated.

In the demonstration, the receipt REC-20261026-006 for the lot LOT-20261026-004 of Miel Pure announced 48 good and 2 damaged, and 47 units entered the stock after the correction described next.

### Correcting the quantities

The assistant may have put a broken unit in **Good**. You can change the four boxes before you decide, and the change is kept in the history of the receipt.

1. Select the receipt and type the right numbers in the boxes {1} and {2} of the line.
2. Select [[Save corrections]] {3}. The button appears only when a box differs from what the assistant typed.
3. Select [[Validate]] {4}.

![Correcting a line before the validation](figures/correct.png)

The page answers "Corrections saved." after the first button. If you select [[Validate]] without saving, the corrections are saved first and then the receipt is validated. In the figure, 26 units were entered and the controller moved 3 of them from **Good** to **Damaged**: 23 good and 3 damaged, total 26.

Two limits apply to a correction.

- The total of a line cannot exceed the expected quantity. The line then shows "The line total exceeds the expected quantity." under the product name, and nothing is sent.
- A correction can only reduce the total typed by the assistant or move units from one box to another. It cannot add. If the assistant typed 25 on a line that expected 30, and you type 28, the server refuses and the page shows the name of the product followed by the reason: "Miel Pure : A correction can only reduce or redistribute the quantities (current total 25, requested 28)."

> Note: The red message under a line disappears as soon as you change a box of that line. It comes back at the next attempt if the figures are still refused.

### Rejecting a receipt

Reject a receipt when the goods or the paper do not match what was entered and you cannot settle it with a correction, for example when the delivery note is not signed.

1. Select the receipt and select [[Reject]].
2. In the window **Reject**, type the reason in **Rejection reason**.
3. Select [[Reject]] in the window.

If the reason is empty, the window answers "The reason is required." and nothing is sent. Otherwise the page answers "Rejected." and the receipt leaves the queue. Nothing was added to the stock. The assistant receives a notice that carries your reason, so write a sentence that tells what to do next. The assistant then enters a corrected receipt.

### Your own entries

You cannot validate or reject an entry that you wrote yourself. On the screen the entry carries the label **Your entry**, the buttons are hidden, and a yellow band says "You entered this item: another controller must validate it." The server applies the same rule: it refuses with "You cannot decide on an entry you made yourself." You cannot cancel the entry of another person either. In daily work you meet this rule little, because you do not enter pharmacy receipts. It matters for the administrator, who can do both.

## Checking a damage report

A damage report removes from the stock units that are already on the shelf, because they were broken, lost or found defective. Goods that arrive broken belong to the receipt, not to a damage report. Open the tab **Damages** of **To check**.

![The damage reports waiting for a decision](figures/damages.png)

The tab {1} shows the number of reports waiting. Each line gives the date, the product, the type (**Damaged**, **Lost** or **Defective**), the quantity, the reason written by the assistant and the author {2}. [[Validate]] {3} and [[Reject]] {4} are on the line. There are no quantity boxes: a report is accepted or refused as it stands.

1. Read the reason. If it is vague or the quantity looks high, check the shelf.
2. Select [[Validate]] and confirm the question "Confirm validation? Stock will be updated."

The page answers "Validated: stock has been updated." The quantity is taken off the stock, and a movement of the matching type is written with the number of the report and its reason. In the demonstration, a report of 2 lost boxes of Efferalgan lowered the stock by 2 and appears in **Movements**.

To refuse a report, select [[Reject]] and type the reason, as for a receipt. The reason reaches the assistant in the bell. In the demonstration, a report of 4 loose-capped jars of honey was refused because photos were needed first.

### When the stock is too low

A report cannot take the stock below zero. If the assistant declared 5 lost items of a product whose stock is 0, [[Validate]] fails and the page shows, in French, "Stock insuffisant pour Api1 : 0 disponible(s), 5 demandé(s)."

The message means that the system holds fewer units than the report. The report stays in the queue. Either the stock figure is wrong, in which case the physical count is the way to correct it, or the report is wrong. Select [[Reject]] and say which. You cannot cancel it, because only the author or the administrator can.

## Movements

**Movements** is the journal of the pharmacy and natural stock. It answers the question "why does this product show this number?"

![The movements of one product](figures/movements.png)

The search box {1} and the list **Product** {2} find a product. **Movement type** {3} limits the list to one kind, and **From** and **To** limit it by date. [[Filter]] applies the choices and [[Reset]] clears them. Each line gives the date and time (day, month, year), the product, the type {4}, the signed quantity, a note and the author {5}. Red quantities lower the stock and green ones raise it. The types are Sale, Sale cancellation, Initial stock, Correction, Restock and Receipt, and one type for each kind of damage report: damaged, lost and defective.

Two details help when you read it. The author is shown with his or her full name. The notes are written by the server and are often in French, such as "Avarie #1309 (perdu)", which reads "Damage report 1309 (lost)". A validated receipt writes one line per product, and it lists the damaged, lost and defective units in the note.

## Notifications

The bell at the top right keeps your notices. The red number counts the unread ones, and a pop-up such as "You have 15 new notifications" appears when you open a page after some arrived.

The bell lists one entry for each new receipt or damage report, with the name of the author: "Demo Assistant recorded receipt REC-20261026-011 to check" or "Demo Assistant recorded a damage report (Api1, 5) to check". Selecting an entry opens **To check**. The notice tells you that something waits, and the queue shows what. If the bell and the queue disagree, trust the queue and select [[Refresh]].

## Laboratory deliveries

The laboratory stock is separate from the pharmacy stock. It holds reagents and consumables, and it has its own products, receipts and history. The technician and the promoter guides describe the rest of it. You enter the deliveries, and nobody checks them afterwards: the stock rises as soon as you confirm. Be as careful here as the assistant must be with you.

### Reading the products and the requests

**Lab products** lists the products with their packaging, supplier, stock, threshold and last count date. You can add a product with [[Add a product]] and change one with [[Edit]]: name, packaging, supplier, threshold, and the box **Active product** to retire it. The stock is not a field you can type. It starts at 0 and changes through deliveries and counts. A new product created with a threshold above 0 appears at once in **To order**, since its stock of 0 is under the threshold. You cannot send a report on a product, which is the technician's action.

**To order** is read-only for you. It lists the requests, and the filter **Status** opens on **Open**. The column **Origin** tells how the request was born: "Report (Almost out)", "Report (Out)", "Threshold reached" or "Expiry", the last one when a lot of the product enters the 60 days before its expiry date. The status goes from **To order** to **Ordered**, **Received** or **Cancelled**. When you enter a delivery that contains the product, its open request becomes **Received**, whatever the quantity. In the demonstration, a delivery of 5 boxes closed a request for 10.

### Entering a delivery

Keep the supplier invoice in front of you. Select **Lab receipts** to see the receipts already entered.

![The list of laboratory receipts](figures/lab-receipts.png "small")

[[New receipt]] {1} opens the form. The filter **Supplier** {2}, with **From** and **To**, narrows the list, and [[Filter]] applies it. The column **Invoice no.** {3} and the column **Status** {4} (**Valid** or **Cancelled**) identify each receipt. [[Details]] {5} opens the lines in a read-only window. You cannot cancel a receipt: only the administrator can, so a mistake after confirmation goes to the administrator.

1. Select [[New receipt]].
2. Type the invoice number in **Invoice no.** {1} and the supplier in **Supplier** {2}. The supplier box suggests the names already used.
3. Check the **Delivery date** {3}. It opens on today.
4. Select [[Add a product]] {4}, type a few letters in the search box, and select the product. Repeat for each line of the invoice. If the product does not exist yet, the window offers [[Create a product]].
5. On each line, type the quantity ordered if you know it, the quantity received, the lot number, the expiry date and the unit price. The line total and the **Invoice total** are computed for you.
6. Tick the box **Checked** {5} when you have verified the line against the goods.
7. Select [[Confirm receipt]] {7}.

![The form for a laboratory receipt](figures/lab-receipt-form.png)

The box {6} is **Qty received**, the quantity that enters the stock. The button stays pale until the invoice number, the supplier, the date and, on every line, the quantity, the lot, the expiry date and the price are filled in. Every line must also have its **Checked** box ticked: otherwise the button stays pale and the form says "Tick every received line before confirming".

The page answers "Receipt saved." and the new line appears at the top of the list. In the demonstration, a delivery of 20 urine test strips and 9 glucose kits raised their stock from 30 to 50 and from 58 to 67.

An invoice number can be used only once for a supplier. If you type a number that already has a valid receipt for that supplier, the form shows the banner "Invoice already recorded" and nothing is saved.

The sentence under the title is in French: "Une réception valide existe déjà pour ce fournisseur et ce numéro de facture." (a valid receipt already exists for this supplier and invoice number). Check the paper. It is either a duplicate to drop or a typing error in the number.

### The history and the alerts

**Lab history** is the journal of the laboratory stock. It lists receipts, counts and cancellations.

The list **Product** limits it to one product. The column **Type** says Receipt, Count or cancellation, **Stock after** gives the quantity once the movement was applied, and **Reference** gives the number of the receipt or of the count. Receipts entered by you carry your name. A count that confirms the system figure writes no line in this journal.

**Lab alerts** has its own entry in the group **Lab stock**.

![The laboratory alerts](figures/lab-alerts.png)

The card **Weekly count** {1} says how long ago the last count was made. **Low stock** {2} lists the products at or below their threshold, and **Upcoming expiries** {3} lists the lots that expire within 60 days, with the number of days left, the quantity received in that lot and the current stock of the product. The remainder per lot is not tracked, so the two figures are indications. The screen only reads: it has no button that changes anything for you. Open it when you start your week, because the notices about low stock and expiries go to the promoter and the toxicology manager, not to you.

## Working without a connection

The screens of this guide read and write on the server. They keep no copy on the computer. The indicator at the top reads **Connected** while the server answers and **Offline** when the network is lost; for your role it checks the server about every 15 seconds. When it reads **Offline** it adds "(your entries are saved)" on a wide screen. That sentence is true for other roles and not for yours: nothing you type is kept on the computer.

![To check without a connection](figures/offline.png "small")

When the computer cannot reach the server, **To check** shows a red band "Unable to load data." {2}, the tabs read **Receipts (-)** and **Damages (-)** instead of a number, and the list says "No receipt to check." This does not mean that nothing waits. The same holds for the other screens. If the connection drops while you decide on an entry, the button answers with an error and the entry stays in the queue, unchanged.

> Caution: Never conclude from an empty queue that there is nothing to check. Reload the page after a network cut, and select [[Refresh]], before you act. A correction typed in the boxes and not saved is lost when you reload.

## Your profile and password

The account icon at the top right, next to the bell, opens **My Account**.

1. Select the account icon.
2. On the **Profile** tab, correct the full name, the e-mail address or the phone number.
3. Select [[Save]].

The user name and the role cannot be changed here. To change your password, open the **Password** tab, type the current password, then the new one twice, and select [[Save]]. Choose a password of at least 8 characters. Select **Logout** at the end of the day, mostly on a computer that other people use.

## Common mistakes

**Validating without looking at the table.** The assistant may have counted a broken unit as good. Only **Good** raises the stock, so a wrong figure stays in the stock until the next physical count.

**Rejecting without a useful reason.** The reason is the only thing the assistant reads. "Wrong" gives nothing to act on. Say which figure or which paper is the problem.

**Trying to fix a receipt by raising a number.** A correction can only lower the total or move units between the boxes. If more units arrived than the assistant typed, reject the receipt and ask for a new one.

**Expecting a second check on laboratory deliveries.** Nobody validates them after you. A wrong quantity or price goes into the stock and the history, and only the administrator can cancel the receipt.

**Reading an empty queue after a network cut.** See the chapter on working without a connection.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| A page that says 403 and "Access denied" | The screen is closed to your role | Select the button back to your dashboard. |
| "Unable to load data." and empty tabs | The computer cannot reach the server | Wait for the network, then reload the page. |
| "The line total exceeds the expected quantity." | The four boxes add up to more than expected | Lower a box, then select Validate or Save corrections again. |
| "A correction can only reduce or redistribute the quantities" after a product name | You raised the total typed by the assistant | Keep the total or lower it, or reject the receipt. |
| "The reason is required." | The rejection window was sent empty | Type the reason, then select Reject. |
| "Stock insuffisant pour ..." | The report removes more than the stock holds | Reject the report with a reason, or correct the stock first. |
| "You cannot decide on an entry you made yourself." | You entered the item yourself | Ask another controller or the administrator. |
| "Invoice already recorded" | A valid laboratory receipt has this supplier and number | Check the paper, then drop the duplicate or fix the number. |
| "Operation failed." after a button | The connection dropped as you sent | Keep the page open and try again when the network is back. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Damage report
: The declaration that goods already on the shelf were damaged, lost or defective. You validate it before the stock falls.

Good
: The quantity of a receipt line that can be sold or used. Only this quantity enters the stock.

Lot
: A group of finished units with one lot number and one expiry date. The application numbers the lots made by the production unit LOT, then the date and a running number.

Movement
: One line of the journal of a stock: a sale, a receipt, a damage report, a correction. Each line gives the signed quantity and its author.

Receipt
: The record of a delivery. For the pharmacy it is written by the assistant and checked by you. For the laboratory it is written and confirmed by you.

To check
: The status and the screen of an entry that waits for a decision. The stock has not moved yet.
