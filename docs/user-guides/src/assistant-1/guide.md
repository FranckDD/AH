---
title: Production lots and receipts
role: Assistant
subtitle: Receiving the finished lots from the production unit, entering supplier deliveries, declaring damaged goods on the shelf, reading the stock and its history, and knowing what the screens do without a connection.
version: 27 October 2026
output: assistant-1-production-lots-receipts
---

## Before you start {.unnumbered}

This guide is for the assistant of the centre. In Glostone-Care the assistant is the person who stands between the goods and the stock: you receive what the production unit delivers and what suppliers bring, you write down what really arrived, and you declare what was broken or lost. The application then asks a second person, the stock controller, to check your entry. The stock figure changes only after that check. This guide follows one delivery from the finished lot to the validated receipt.

The screenshots come from a demonstration installation. The products, suppliers and quantities in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the assistant can see and do

The application opens on the **Toxicology Dashboard**. Your menu has three groups. **Toxicology Dashboard** and **Toxicology Monitoring** belong to the toxicology programme: you can read the list of patients, open their files and admit a patient, but you cannot discharge one. The toxicology manager's guides describe those screens, and nothing about them is repeated here. The third group, **Stock management**, unfolds five screens: **Stock Management**, **Production**, **Receipts**, **Damages** and **Movements**. This guide covers the last four. **Stock Management** is the list of pharmacy and natural products, with their quantity and price.

You cannot validate or reject a receipt or a damage report, and you cannot change a quantity by hand. The stock controller does the check. The screens of the fabrication unit, the laboratory stock, the physical count, the patients and the dashboards of the administration are closed to you: if you type the address of one of them, the application shows a page that says 403 and "Access denied", with a button "Go to my dashboard".

> Note: You see every production lot, but only the receipts and damage reports that you entered yourself. A colleague's entries do not appear in your lists.

![The menu of the assistant](figures/menu.png "small")

Select **Toxicology Monitoring** {1} for the patients. The group **Stock management** {2} stays unfolded while you work in it, and the highlighted entry shows where you are. {3} opens the pharmacy list, {4} the production lots, {5} the receipts, {6} the damage reports and {7} the history of movements.

### Signing in

Each member of staff has a personal account. Ask the administrator for yours.

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]].
3. Type your password in [[Password]].
4. Select [[Sign in]].

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again.

### Interface language

Select **EN** in the language switch at the top right, next to the bell, to work in English. The choice is kept on that computer. A few server messages about lots stay in French; this guide quotes them as they appear.

## From the finished lot to the stock

Two kinds of goods reach the stock through you. The first is a lot made by the production unit of the centre. The second is a delivery from an outside supplier. Both end the same way: you write a receipt, the stock controller checks it, and the quantities you called good are added to the stock.

For a manufactured lot the path has five steps.

1. The production manager finishes a batch and ships it. A lot appears in your **Production** list with the status **Produced**, its quantity, its expiry date and the name of the producer.
2. When the bottles are physically in your hands, you mark the lot as delivered. Its status becomes **Delivered**.
3. You open a receipt for that lot and type how many bottles are good, damaged, lost or defective.
4. The stock controller counts or inspects, then validates the receipt. The good bottles enter the stock, and the lot becomes **Received**.
5. If the controller rejects the receipt, the lot stays **Delivered**. You correct the figures in a new receipt.

A delivery from a supplier skips the first two steps: you open a receipt directly and give the supplier name and the products.

| Status | Where | Meaning |
|---|---|---|
| Produced | Lot | The lot was made and shipped. Nothing has arrived yet. |
| Delivered | Lot | The lot is in your hands and no receipt is open for it. |
| Received | Lot | A receipt for the lot was validated. The stock has risen. |
| Cancelled | Lot | Someone closed the lot. |
| To check | Receipt or damage report | You entered it. The controller has not decided. |
| Validated | Receipt or damage report | The controller accepted it and the stock moved. |
| Rejected | Receipt or damage report | The controller refused it, or you cancelled it. The reason is shown. |

## Production lots

Select **Production** to see every lot, the most recent first. The title counts the lots that are not cancelled and, in brackets, the cancelled ones, for example "3 batches (1 cancelled)".

![The list of production lots](figures/lots.png)

[[New lot]] {1} creates a lot by hand. The filter **Status** {2} narrows the list to one status. The column **Status** {3} shows where each lot stands. On a lot that was only produced, [[Mark delivered]] {4} is offered, and [[Cancel]] {5} too when the lot is yours. A lot that is delivered offers [[Cancel]] only, and a lot that is received or cancelled offers nothing.

The lot number, such as LOT-20261026-001, is given by the application: the date and a running number for the day. The columns **Delivery date** and **Expiry** carry what the production manager typed when the batch was shipped.

### Marking a lot as delivered

1. On the line of the lot, select [[Mark delivered]].
2. Check the date in **Delivery date**. It opens on today. Change it if the bottles arrived on another day.
3. Select [[Confirm]].

The page answers "Lot marked as delivered." and the status becomes **Delivered**. The lot can now be chosen in a receipt. A lot that is not marked cannot be received.

### Creating a lot yourself

Most lots arrive from the production unit. Create one by hand only for goods made outside that unit, for example by a partner who delivers finished jars.

1. Select [[New lot]].
2. Choose the product. The list holds the products of the pharmacy and natural stock.
3. Type the quantity produced. It is a whole number above zero.
4. Check the production date. It opens on today.
5. Type the delivery date and the expiry date if you know them, and the producer.
6. Select [[Save]].

If the product is missing, the window shows "Choose a product." and nothing is saved. When the lot is saved, the page answers "Lot saved." and the lot appears at the top with the status **Produced**. A lot created by hand has no delivery date until you mark it as delivered.

### Cancelling a lot

Select [[Cancel]] on the line and confirm the question "Confirm cancellation?". The page answers "Cancelled." and the status becomes **Cancelled**. Two rules apply.

- Only the person who created the lot, or the administrator, can cancel it. The button [[Cancel]] is therefore shown only on the lots you created. A lot shipped by the production manager has no Cancel button on your screen.
- A lot that has a receipt open or validated cannot be cancelled. Cancel the receipt first, if it is still waiting for its check.

When the server refuses, the message is written in French: "Une réception est liée à ce lot : annulation impossible." (a receipt is linked to this lot). The lot is left as it was.

## Receipts

A receipt is the written record of what arrived. Select **Receipts** to see yours.

![The list of receipts](figures/receipts.png)

[[New receipt]] {1} opens the form. The filter {2} offers **To check**, **Validated** and **Rejected**. The column **Lot / supplier** {3} names the lot or the supplier, and the column **Origin** says which of the two it is. The column **Status** follows the check: a **Validated** receipt {4} has been accepted, and a rejected one shows its reason {5} under the status. [[Details]] {6} opens the lines of the receipt, read-only, with the expected, good, damaged, lost and defective quantities, the lot number and the expiry. To correct a receipt that is still waiting for its check, cancel it and enter a new one. While a receipt is waiting for its check, [[Cancel]] also appears next to [[Details]].

### Receiving a manufactured lot

1. Select [[New receipt]]. The form opens with **Manufactured lot** {1} chosen.
2. Check the **Reception date** {2}. It opens on today.
3. In **Choose a delivered lot** {3}, pick the lot. Only lots with the status **Delivered** and no open receipt are offered. If there is none, the form says "No delivered lot awaiting reception."
4. The line fills itself with the product, the expected quantity (the quantity produced), the lot number and the expiry date. Only the four quantity boxes are yours to type.
5. Type the number of good bottles in **Good** {4}. Type the broken bottles in **Damaged**, the missing ones in **Lost** and the bottles that cannot be sold in **Defective** {5}. A box left at 0 means none.
6. Read the **Total** {6}. It is the sum of the four boxes.
7. Select [[Save]].

![The receipt form for a manufactured lot](figures/receipt-form.png)

The page answers "Receipt saved, awaiting check." and the receipt appears with the status **To check**. The stock has not moved yet.

The form refuses two kinds of total, and says so in red under the line. "The line total exceeds the expected quantity." appears when the four boxes add up to more than the lot holds. "The line total must be greater than 0." appears when every box is 0. Correct the figures before you select [[Save]].

> Caution: Only the **Good** bottles enter the stock. The damaged, lost and defective ones are recorded on the receipt, and they appear in the note of the stock movement, but they add nothing. Count each bottle in the right box.

### Receiving a supplier delivery

1. Select [[New receipt]] and choose **Supplier** {1}.
2. Type the supplier name {2}. It is required: without it the form answers "The supplier is required."
3. Type the reference of the delivery note in **Delivery ref.** {3}. It is optional but helps the controller find the paper.
4. On the first line, choose the product {4} and type the quantity written on the delivery note in **Expected**.
5. Type the four quantities as for a manufactured lot. The total cannot exceed **Expected** when you filled it.
6. Type the supplier's lot number {5} and the expiry date if they are printed on the boxes. Both are optional.
7. For a second product, select [[Add a line]] and repeat. [[Remove line]] deletes a line once there are two or more.
8. Select [[Save]].

![The receipt form for a supplier](figures/receipt-supplier.png)

In the demonstration, a delivery of two products was saved in one receipt: 50 Efferalgan with 48 good and 2 damaged, and 30 Carnet 2, all good. Use one receipt for one delivery note.

### Cancelling a receipt

While the status is **To check**, [[Cancel]] and the question "Confirm cancellation?" close the receipt. The page answers "Cancelled." Only its author, or the administrator, can do it.

A cancelled receipt does not vanish. It stays in the list with the status **Rejected** and the reason "annulé par l'auteur" (cancelled by the author), written in French. A lot whose receipt was cancelled can be received again.

### What happens after the check

The stock controller opens the receipt and either validates or rejects it. The status changes on the line, as in the figure above, and the bell receives a notice.

A validated receipt has done its work. The good quantities are added to the stock of each product, a line **Receipt** is written in the movements, the lot becomes **Received**, and the earliest expiry date among the old and the new boxes is kept on the product. A rejected receipt shows the reason typed by the controller. Nothing was added to the stock. The lot is available again in the form, so you can enter a corrected receipt.

## Damages

A damage report removes goods that are already on the shelf, because they were broken, lost or found defective. Use it for stock that was received and validated earlier. Goods that arrive broken belong to the receipt, in the columns **Damaged**, **Lost** and **Defective**.

Select **Damages** to see your reports, with the filter by status as in the receipts.

1. Select [[Declare damage]].
2. Choose the product {1}.
3. Choose the type {2}: **Damaged**, **Lost** or **Defective**.
4. Type the quantity {3}, a whole number above zero.
5. Write the reason {4}. It is required: say what happened in one sentence.
6. Check the date {5}. It opens on today.
7. Select [[Save]] {6}.

![The form for a damage report](figures/incident-form.png "small")

The page answers "Damage declared, awaiting check." and the report appears with the status **To check**. The stock has not changed yet. If the product is missing, the window answers "Choose a product."

The controller validates or rejects the report. On validation, the quantity is taken off the stock and a movement of the matching type is written. In the demonstration, a report of 3 crushed boxes of Efferalgan lowered the stock by 3 once validated. The check also protects the stock from going below zero: a report of 5 lost items on a product that has none was refused to the controller with "Stock insuffisant pour Api1 : 0 disponible(s), 5 demandé(s)." The report stays **To check**, and it is for you to cancel it. [[Cancel]] works exactly like the cancellation of a receipt, and the report then shows **Rejected**.

## Stock and movements

### The stock list

**Stock Management** lists the pharmacy and natural products with their category, quantity and unit price, and tiles that total the stock value and count the low and expired products. The search box and the category filter narrow the list. A line that is at or under its alert threshold shows a red **LOW** label, and an expired date shows in red.

[[Edit]] opens a product. You can change the name, the category, the selling price, the alert threshold ("Alert Threshold (Min)") and the expiry date, and confirm with [[Update]]. The quantity is shown but cannot be typed: the window says "Quantity only changes through a checked receipt, a damage report or an adjustment request." When the stock list cannot be loaded, the tiles show a dash and a message with a **Retry** button, instead of zeros.

Two buttons of the list concern the barcode labels that are stuck on every product. [[Print labels]] opens a window where you tick the products, type the number of labels, choose a label roll or an A4 sheet with cut marks, check the preview and print. [[Label]] on a row prints the label of that product alone. In the product window, the section **Photo and code** shows the 8-digit code of the product and lets you add, replace or remove its photo (JPEG, PNG or WebP, up to 5 MB). The first guide of the administrator describes these screens with figures.

### The history of movements

**Movements** is the journal of the stock. It answers the question "why does this product show this number?"

![The movements of one product](figures/movements.png)

The search box {1} and the list **Product** {2} find a product. **Movement type** {3} limits the list to sales, receipts, damages, corrections and so on, and **From** and **To** limit it by date. [[Filter]] applies the choices and [[Reset]] clears them. Each line gives the date (day, month, year and time), the product, the type {4}, the signed quantity, a note and the author {5}, shown with his or her full name. Red quantities lower the stock and green ones raise it. The page shows 50 lines and a page selector when there are more.

In the demonstration, the validated receipt of 48 Efferalgan and the validated damage report of 3 appear at the top of the list with the name of the controller. The notes are written by the server in French, for example "Réception REC-20261026-003 (avaries : endommagé 2)". Read them as "Receipt REC-20261026-003 (damages: damaged 2)".

## Notifications

The bell at the top right keeps your notices. The red number is the count of unread ones, and a pop-up "You have 4 new notifications" appears when you open a page after some arrived.

![The bell with four decisions](figures/bell.png "small")

The bell {1} lists the decisions on your entries {2}: "Receipt REC-20261026-012 validated", "Receipt REC-20261026-011 rejected (reason: ...)" and "Receipt REC-20261026-009 validated". A damage report decision reads "Damage report AVA-1307 validated" in the same way. A notice for a rejection carries the reason, so you do not need to open the receipt to read it. You are not told when you cancel your own entry.

## Working without a connection

The screens of this guide read and write on the server. They keep no copy on the computer. The indicator at the top reads **Connected** while the server answers and **Offline** when the network is lost. For your role it checks the server about every 15 seconds. When it reads **Offline** {1}, it says nothing more: unlike the roles that keep a copy, nothing you type is kept on the computer.

![Production lots without a connection](figures/offline-lots.png)

When the computer cannot reach the server, **Production** shows a red band "Unable to load data." {2} and "No lots." {3}, and the title counts 0 batches. This does not mean that there are no lots. If you open [[New lot]] in that state, the product list is empty and the window says "Unable to load the product list." Nothing you type is kept for later.

If the connection drops while a form is open, selecting [[Save]] shows "Operation failed." and the typed values stay in the window. Wait until the network is back and select the button again. Do not close the window before that.

> Caution: Never conclude from an empty list that nothing arrived. Reload the page after a network cut before you act.

## Your profile and password

The account icon at the top right, next to the bell, opens **My Account**.

1. Select the account icon.
2. On the **Profile** tab, correct the full name, the e-mail address or the phone number.
3. Select [[Save]].

The user name and the role cannot be changed here. To change your password, open the **Password** tab, type the current password, then the new one twice, and select [[Save]]. Choose a password of at least 8 characters. Select **Logout** at the end of the day, mostly on a computer that other people use.

## Common mistakes

**Marking a lot as delivered before the goods are in your hands.** The lot then appears in the receipt form, and a colleague may receive goods that are not there. Mark it when you hold the bottles.

**Counting everything as good.** Only the **Good** boxes raise the stock. A broken bottle typed as good overstates the stock until the next physical count.

**Looking for a receipt that a colleague entered.** You see only your own. Ask the stock controller, who sees all of them.

**Expecting the stock to move when you save.** It moves when the controller validates. A receipt cannot be edited or cancelled by you after that: tell the stock controller or the administrator.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| A page that says 403 and "Access denied" | The screen is closed to your role | Select the button back to your dashboard. |
| "Unable to load data." and "No lots." | The computer cannot reach the server | Wait for the network, then reload the page. |
| "Operation failed." after Save | The connection dropped as you sent | Keep the window open and select Save again later. |
| "Une réception est liée à ce lot : annulation impossible." | A receipt exists for the lot | Cancel the receipt if it is still To check. |
| "The line total exceeds the expected quantity." | Good, damaged, lost and defective add up to more than expected | Recount and correct the boxes. |
| "No delivered lot awaiting reception." | No lot is marked Delivered, or each already has a receipt | Mark the lot as delivered in Production. |
| A receipt is Rejected with a reason | The controller refused it | Read the reason, then enter a corrected receipt. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Damage report
: The declaration that goods already on the shelf were broken, lost or defective. The controller must validate it before the stock falls.

Good
: The quantity of a receipt line that can be sold. Only this quantity enters the stock.

Lot
: A group of finished units with one lot number and one expiry date. The application numbers them LOT-date-number.

Receipt
: The record of a delivery, written by you and checked by the stock controller. A validated receipt raises the stock.

Stock controller
: The person who checks receipts and damage reports. The controller cannot validate an entry that he or she wrote.
