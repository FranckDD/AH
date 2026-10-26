---
title: Laboratory stock and weekly count
role: Laboratory technician
subtitle: Keeping the list of reagents and consumables, reporting a product that is almost out, following orders and deliveries, counting the stock every week, reading alerts and history, and knowing what the screens do without a connection.
version: 26 October 2026
output: lab-2-stock-weekly-count
---

## Before you start {.unnumbered}

This is the second guide for the laboratory technician. The first one follows a patient request from reception to the validated result sheet. This one covers the stock of reagents and consumables that the laboratory uses to produce those results: the list of products, the report you send when a product is nearly finished, the orders that follow, the deliveries, the weekly count and the alerts. Nothing about requests or results is repeated here; open the first guide for that.

The screenshots come from a demonstration installation. The products, suppliers and quantities in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the technician can see and do

Your menu has two entries: **Laboratory** and **Lab stock**. This guide covers the second. Selecting **Lab stock** unfolds four screens: **Lab products**, **To order**, **Lab count** and **Lab alerts**.

You can add and edit products, report a product as almost out or out, count the stock, and read the orders and the alerts. You cannot place an order, change an order date or cancel an order: the promoter and the toxicology manager do that. You cannot enter a delivery. The stock controller and the promoter do that on screens that are closed to you: if you type the address of the receipts screen, the application answers with a page that says 403 (access refused). The laboratory expenses screen is closed to you in the same way.

> Note: A sixth screen, **Lab history**, is open to you but has no menu entry. The chapter on history explains how to reach it.

### Interface language

The application starts in French on a new computer. Select **EN** in the language switch at the top right, next to the bell, to work in English. The choice is kept on that computer. Everything in the stock screens is available in English, with one exception: some error messages written by the server stay in French. This guide quotes them as they appear.

### The connection

The stock screens read and write directly on the server. Unlike the laboratory results, they have no copy on the computer. The last chapter explains what you see when the connection drops.

## The list of products

A product is an item that the laboratory buys and uses: a reagent kit, a box of tubes, a bottle of test strips. Each product has a name, a packaging, a supplier, an alert threshold and a stock. Open **Lab products** to see them.

![The list of laboratory products](figures/products.png "small")

The menu group {1} stays unfolded while you work in these screens. [[Add a product]] {2} creates a new line. The search box {3} filters the list by name, packaging or supplier as you type. The column **Stock** {4} shows the quantity the application holds. A product whose stock is equal to or lower than its threshold shows a red **Low** label next to the quantity. The column **Last count** gives the date of the last weekly count that included the product, or "never". On each line, [[Report]] {5} sends a stock report and [[Edit]] {6} opens the product.

The stock you read here is not typed by hand anywhere. It moves in two ways only: a delivery adds to it, and a count sets it to the quantity you counted. The next chapters describe both.

### Adding a product

1. Select [[Add a product]].
2. Type the name in [[Product]] {1}. The name is required.
3. Type the packaging {2} and the supplier {3}. Both are optional but help the person who orders.
4. Type the alert threshold in [[Threshold]] {4}. This is the quantity at or below which the product counts as low. It is required and must be a whole number, zero or more.
5. Select [[Save]] {5}.

![The form for a new product](figures/product-form.png "small")

The page answers "Product saved." and the new line appears in the list. The form says it in one sentence: the stock starts at 0 and changes through deliveries and counts. A new product therefore shows **Low** straight away. This is normal, and no order is created for it until a delivery or a count leaves it at or under its threshold.

Two products cannot carry the same name while both are active. The server then refuses the second one with a message in French: "Un produit actif nommé « Pipette tips » existe déjà." (an active product with this name already exists). Choose another name, or edit the first product.

### Editing or retiring a product

1. On the line of the product, select [[Edit]].
2. Change the name, the packaging, the supplier or the threshold.
3. To stop using the product, clear the box [[Active product]] {2}.
4. Select [[Save]] {3}.

![Editing a product](figures/product-edit.png "small")

A product that is no longer active disappears from the list and from the weekly count, and it can no longer be received. Tick [[Show inactive products]] above the list to see it again. Its line then carries an **Inactive** label and has no [[Report]] button, only [[Edit]]. Tick **Active product** again to bring it back.

> Caution: A retired product keeps its stock quantity but is not counted any more, and its lots no longer appear in the expiry list. Retire a product only when the laboratory has stopped using it.

## Reporting a product that is almost out

The threshold warns by itself, but only when someone counts or when a delivery arrives. When you open the last box and see that the product will not last the week, report it without waiting for the count.

1. In **Lab products**, find the product and select [[Report]].
2. In the window **Report the product status**, choose [[Almost out]] {1} if some stock remains but will not last, or [[Out]] {2} if nothing is left.

![The report window](figures/signal.png "small")

The window closes and the page answers "Report sent." The report creates a line in **To order** with the origin "Report" followed by the level you chose. The promoter and the toxicology manager each receive a bell entry, "Lab: [product] almost out" or "Lab: [product] is out". They order the product.

Only one open request exists for a product at any time. If you report the same product again while its request is still open, the application changes the level of that request and does not create a second one. This is the way to correct a report: report again with the other level.

## Following the orders

Open **To order** to see what has been asked and where each request stands. The screen is read-only for you. It exists so that you know whether the product you reported is on its way.

![The list of requests](figures/requests.png "small")

The menu entry {1} is highlighted for the screen you are on. The filter **Status** {2} opens on **Open**, which lists the requests that are still waiting (To order and Ordered). The other choices are To order, Ordered, Received, Cancelled and All. The column **Origin** {3} tells how the request was born, and the column **Status** {4} says where it stands. **Expected date** {5} is the delivery date that the person who ordered gave.

There are three origins.

| Origin | How it is created |
|---|---|
| Report | You, or a colleague of the laboratory, used the Report button. The level is written in brackets: Almost out or Out. |
| Threshold reached | A count or a delivery left the stock at or below the threshold and no request was open. The application creates it by itself. The promoter and the toxicology manager receive the bell entry "Lab: [product] below threshold". |
| Expiry | Foreseen by the application, but no action creates it today. You should not meet it. |

A request goes through four statuses. **To order** means nobody has placed the order. **Ordered** means the promoter or the toxicology manager marked it with an expected date. **Received** means a delivery that contained the product was entered. **Cancelled** means someone closed it with a reason, which is shown under the status.

A request that the application created by itself because of the threshold can cancel itself too. In the demonstration, a count that raised a product from 3 to 30 closed its "Threshold reached" request, with the reason "stock remonté" (stock went up). A request that came from a report is not cancelled by a count, because a person asked for it.

> Note: The title says "(4 requests)" even when there is one. The count is right, the plural is not.

## Deliveries

You do not enter deliveries, but you see their effect, so it helps to know what happens at the other desk. The stock controller, or the promoter, receives the goods and fills a receipt that copies the supplier invoice. The promoter guide describes the form step by step. In short, the person types the invoice number, the supplier and the delivery date, adds each product of the invoice, then types for each line the quantity received, the lot number, the expiry date and the unit price, and ticks the line to say that the goods were checked.

![A receipt being filled by the stock controller](figures/receipt-form.png "small")

The figure shows the form filled by the stock controller for an invoice of three products. The fields {1} and {2} carry the invoice number and the supplier. [[Add a product]] {3} adds a line, the box {4} confirms that the line was checked, and [[Confirm receipt]] {5} saves everything. The lot number and the expiry date are required on every line.

When the receipt is saved, you notice four things.

1. The stock of each product in the receipt goes up by the quantity received. The change is recorded in the history as a **Receipt**.
2. Any request open for these products becomes **Received**, whatever the quantity. A delivery of 20 units closes a request for 100 units.
3. If you were the person who reported the product, you receive a bell entry: "Lab: delivery from [supplier] (1 reported product(s))". Selecting it opens **Lab products**. A request that the application created from the threshold does not notify anyone at delivery.
4. If the stock is still at or below the threshold after the delivery, the application opens a new "Threshold reached" request at once.

A receipt cannot be cancelled by the people who enter it. Only the administrator can. If you see a wrong quantity in the stock after a delivery, tell the stock controller or the promoter before you count.

## The weekly count

The count brings the stock held by the application back to what is on the shelves. Do it once a week. The application reminds you when seven days have passed, and the reminder comes in three places.

- A yellow band at the top of **Lab count** reads "The last count was 8 days ago: a count is due." If nobody has ever counted, it reads "Stock never counted: a first count is due."
- The **Weekly count** card in **Lab alerts** turns yellow with the same sentence.
- A bell entry reads "Lab: stock count due (last one 8 day(s) ago)". There is one per week at most, and selecting it opens **Lab count**.

![The count screen before anything is typed](figures/count-empty.png "small")

The title {1} gives the date of the last count in brackets. The band {2} is the reminder. The search box {3} filters the products when the list is long. **Last stock** {4} is the quantity that the application holds now, and **Counted quantity** {5} is the column you fill.

This screen shows the application stock, unlike the physical count of the pharmacy, which hides it. You see both numbers side by side. Count the shelf first, then type the number, and do not copy the application figure.

### Doing the count

1. Select [[Lab count]] in the menu.
2. Count each product on the shelf. Count unopened boxes and the content of opened ones in the same unit as the packaging.
3. Type the quantity in the box of the product {1}. Type whole numbers, zero or more. Leave a box empty for a product that you did not count: it is left alone.
4. Check the line above the table, which reads "4/4 entered" when every box is filled.
5. Select [[Submit count]] {2}.

![The count screen with quantities typed](figures/count-filled.png "small")

The button stays grey until at least one quantity is typed, and stays grey while a box holds something that is not a whole number. The page answers "Count saved" with the number of products between brackets, for example "Count saved (4 product(s)).", and empties the boxes. The stock of every counted product now equals what you typed. A product counted at the same value is recorded too, with a change of 0.

The count never asks you for a reason and never compares your number with a limit, so a typing mistake changes the stock at once. Read each box before you submit.

### When the stock changes during the count

A colleague may receive a delivery while you are counting. The application then protects both numbers. It saves the products that did not change, and it holds back each product whose stock moved since you opened the page.

![A product to recount](figures/count-conflict.png "small")

In the demonstration, the stock controller entered 40 more tubes of EDTA while the count was open. The page saved three products ("Count saved (3 product(s))."), and a yellow band {1} said "Stock changed during the count: recount these products." with the line "EDTA sample tubes: expected 58, new stock 98". The product carries the label **To recount** {2}, and the box keeps the number you typed.

1. Count that product again, because the delivery means the shelf holds more than before.
2. Correct the number in its box.
3. Select [[Submit count]] {3} again.

The page answers "Count saved (1 product(s))." If every product of a submission is in conflict, nothing is saved and the band alone is shown.

### After the count

The stock of the counted products changes immediately, as does the date in the column **Last count**. The reminder bell entry is marked as read, and the band disappears. A product that falls at or below its threshold gets a "Threshold reached" request, and the promoter and the toxicology manager are told. A product that rises above its threshold has its automatic request cancelled, if nobody ordered it yet.

The count is not announced to anyone, and no summary is sent. The people who follow the stock read it in two places: the **Last count** column in **Lab products**, and **Lab history**, where each counted product has a line with its change and the stock after. The next chapter shows that screen.

## Alerts

**Lab alerts** gathers what needs attention. It has no button that changes anything, only links.

![The alerts screen](figures/alerts.png "small")

The card **Weekly count** {1} says when the last count was made. [[Go to count]] {2} opens the count screen. **Low stock** {3} lists every product at or below its threshold with a label such as "Stock 3 / threshold 5", and says under the name whether a request is open ("Request: To order"). A product with a threshold of 0 and no stock is not listed, so that a product you do not use does not raise a false alert. [[Open the to-order list]] leads to **To order**. **Upcoming expiries** {4} lists the lots that expire within 60 days, with the number of days left, and a lot that has already expired in red with "Expired N days ago".

An expiry belongs to a lot that was delivered, not to what is left on the shelf. The list shows every lot of an active product that still has stock, whatever has been used. If a lot is long finished, the line will stay until the product is retired or the stock reaches zero. Compare the lot number with the label on the boxes before you act.

The promoter and the toxicology manager receive a bell entry for each lot at 60 days or less ("Lab: [product] (lot [lot]) expires in [n] day(s)"). You do not receive it. Your only sign is this screen, so open it when you start your week.

### Your notifications

The bell at the top right keeps your stock notifications. Two kinds reach you.

![The bell with two delivery notices](figures/bell.png "small")

The bell {1} shows the number of unread entries. A delivery notice {2} says that a product you reported has arrived. The count reminder is the other kind, described above. Other stock notices, such as low stock or expiry, are for the promoter and the toxicology manager.

## Lab history

**Lab history** lists every stock movement: receipts, count corrections and cancelled receipts. It answers the question "why does the stock read this number?"

The screen has no entry in your menu, although you are allowed to read it. Open it by typing the address of the application followed by /dashboard/lab-stock-movements in the browser, or ask the promoter or the stock controller, who have it in their menu. The figure below shows it.

![The movement history](figures/history.png "small")

The filter {1} limits the list to one product. The column **Type** {2} says Receipt, Count or Receipt cancellation. **Change** gives the difference, in red when the stock goes down and in green when it goes up, and **Stock after** {3} the quantity once the movement was applied. **By** {4} names the person, and **Reference** gives the number of the receipt or of the count. The 200 most recent movements are shown.

Two things can surprise you. A count that confirms the application figure still produces a line, with a change of 0. And one count writes one line per product, all with the same count number, so several lines can share a minute. A large negative change deserves a second look before you submit: in the demonstration, a count removed 17 test strips from the stock at once.

## Working without a connection

The stock screens need the server. This differs from the laboratory results, which you can keep typing offline.

![Lab products without a connection](figures/off-products.png "small")

On a computer that is offline from the start, **Lab products** shows a red band that reads "Unable to load data." and a list with "No products." The yellow indicator at the top still says "Offline (your entries are saved)". That sentence is true for the results, not for the stock screens: nothing you do here is kept for later. The other screens of the group call the server in the same way.

If the connection drops while a screen is open, the product list stays on screen, and so do the quantities you typed. Selecting [[Submit count]] then shows "Operation failed." and nothing is saved. Keep the quantities in the boxes, wait for the indicator to read "Connected" and select the button again. The other buttons of these screens, such as [[Report]] and [[Save]] on a product, call the server too, so the same advice applies.

> Caution: Do not close or refresh the page between a failed submission and the next try. The numbers in the boxes live only on the screen.

## Common mistakes

**Copying the application figure into the count.** The screen shows the stock next to the box. A count that repeats it only confirms an error. Count the shelf.

**Leaving a box empty and thinking it means zero.** An empty box means the product was not counted. Type 0 for a product that is really finished.

**Reporting in place of counting.** A report creates an order, but it does not change the stock. After a delivery, the stock rises, and only the next count corrects any other difference.

**Retiring a product to hide a problem.** A retired product disappears from the count and from the expiry list. Use it for products that the laboratory no longer buys.

**Typing a name that exists.** The server refuses it in French. Look for the existing product first, with the search box.

**Counting during a delivery.** If the stock controller is entering a receipt, finish the other products first and come back to that one.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| A page that says 403 | The screen is closed to your role | Use one of your four screens. Ask the promoter for receipts or expenses. |
| "Unable to load data." and "No products." | The computer cannot reach the server | Wait for "Connected", then reopen the screen. |
| "Operation failed." after Submit count | The connection dropped as you sent | Keep the numbers, wait for "Connected", select Submit count again. |
| "Stock changed during the count: recount these products." | A delivery arrived while you counted | Recount the products marked To recount and submit again. |
| Submit count stays grey | No box is filled, or one value is not a whole number | Type whole numbers, zero or more. |
| "Un produit actif nommé ... existe déjà." | A product with that name is active | Pick another name or edit the existing product. |
| A new product shows Low and has no order | Its stock is 0 and nothing has triggered a request | Wait for the delivery, or report the product yourself. |
| The product you reported is not in To order | The filter is on a status that does not match | Choose All in the Status filter. |
| The count reminder stays after you counted | The count was not saved | Look for a red or yellow band, then submit again. A saved count marks the reminder as read. |
| No Lab history in the menu | The screen has no entry for your role | Use the address given in the History chapter. |

## Glossary {.unnumbered}

Alert threshold
: The quantity at or below which a product counts as low. It is set on each product.

Count
: The weekly operation in which you type the quantity found on the shelf for each product. It replaces the stock held by the application.

Lot
: A group of units from one delivery, with one lot number and one expiry date.

Movement
: One line of the history: a receipt, a count correction or a cancelled receipt.

Receipt
: The entry of a supplier invoice by the stock controller or the promoter. It raises the stock.

Report
: The button that tells the promoter that a product is almost out or out.

Request
: A line of the **To order** screen. It is open until it is received or cancelled.

To recount
: The label put on a product whose stock changed while you were counting.
