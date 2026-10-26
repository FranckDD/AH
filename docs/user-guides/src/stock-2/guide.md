---
title: Physical count
role: Stock controller
subtitle: Counting the shelves of the pharmacy without seeing the system figures, reading the gaps, following the correction requests sent to the administrator, and keeping every product counted on time.
version: 27 October 2026
output: stock-2-physical-count
---

## Before you start {.unnumbered}

This is the second guide for the stock controller. The first one covers the receipts and damage reports entered by the assistant, the movements and the laboratory deliveries. This one covers a single task: the physical count of the pharmacy and natural stock. Signing in, the menu, the bell and the profile are described in the first guide and are not repeated here.

The system keeps a theoretical stock: what came in through validated receipts, minus sales and damage, plus approved corrections. The physical count compares that figure with what is really on the shelves. You are the only role that counts. The administrator decides what to do with the gaps, and the promoter may read the results.

The count is blind. While you count, the screen never shows the quantity the system holds. You type what you see, and the system figures appear only after you validate. This rule protects the count: a person who sees the expected number tends to confirm it.

The screenshots come from a demonstration installation. The products and quantities in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### Where the count is

Open **Stock management** {1} in the menu, then **Stock count** {2}.

![The menu entry for the count](figures/menu.png "small")

The screen has three tabs. **Count** is where you count. **Frequency** tells which products must be counted soon. **History** lists the counts already validated. The same screen is open to the administrator and the promoter, but only you see the **Count** tab.

> Note: The count needs the server. The indicator at the top reads "Connected" while the server answers, and "Offline" when it does not. Nothing typed in the count is kept on the computer, whatever the indicator says. The last chapter explains what happens without a connection.

## Counting the shelves

Count the products on the shelves of the pharmacy, in the order you like, and type the quantities in the application. One count belongs to you alone: you cannot have two counts open at the same time, and nobody else can validate yours.

![The start of a count](figures/start.png)

1. Open **Stock count**. The tab **Count** shows the card **New count**.
2. Select [[Start a count]] {1}.

The page then shows the title "Count no. 1123 in progress" with the time the count started, and one line for each product of the pharmacy. There is no choice of scope: the list always holds every product. What decides which products are counted is what you type. A field left empty reads **Not counted** and the product is simply left out. You may therefore count the whole pharmacy in one go, or only one shelf.

### Typing the quantities

![A count with several quantities typed](figures/count-form.png)

1. Type the quantity you see in the box of the product {2}. Use whole numbers only, from 0 to 10000000.
2. Leave the box, with the Tab key or by selecting another box. The time is noted at this moment for that product.
3. If something explains a difference, select [[Note]] on the line and write a short sentence in the box {3}. Without a note, the application writes its own reason for the request.
4. To find a product quickly, type part of its name in the search box {1}. Quantities already typed are kept while you search.
5. Read the sentence above the green button {4}. It says how many products you counted out of the total, here "5 product(s) counted out of 9."
6. Select [[Validate the count]] {5}.

A zero is a real answer. If the shelf is empty, type 0. Only an empty box means that you did not count the product.

The time noted when you leave the box matters. It is the moment at which the system compares your figure with its own. A sale or a delivery recorded after that moment is not counted as a loss or a surplus, as the next chapter shows.

### When a quantity is wrong

If you type something that is not a whole number, such as 3x, the line turns red and says "Enter a whole number between 0 and 10000000." The green button becomes pale and the sentence above it reads "Fix the invalid quantities before validating." Nothing is sent until every box is right.

### Stopping or resuming

Typed quantities live only on the screen. If you reload the page, close the browser or lose power, the count stays open on the server, but the quantities are gone. After the reload the page shows the same count number with every box empty, and you type again. A count that is still open is also found when you return to the screen on another day.

To drop a count you do not want, select [[Abandon the count]] {6} (top right of the figure of the count form) and answer OK to the question "Abandon this count? Entries will be lost and nothing will be sent." The page answers "The count was abandoned." and offers a new count. An abandoned count produces no gap, no request, and does not appear in the history.

If you try to start a second count while one is open, the server refuses with "Vous avez deja un comptage en cours." (you already have a count in progress). Reopen the screen: the open count is taken up again, and you can finish it or abandon it.

## Reading the result

When you select [[Validate the count]], the page answers "Count no. 1123 validated." and shows the table **Count result**. This is the first time the system figures appear. A validated count cannot be changed.

The result is the same table you find later in the **History** tab, so the figure of the next chapter explains it. Here are its columns.

| Column | What it tells |
|---|---|
| Product | The product, with your note under the name when you wrote one |
| System | The stock the system held at the moment you counted that product, and the time of the count |
| Counted | What you typed |
| Gap | **No gap**, a number **extra** (you found more than the system) or a number **missing** |
| Movements after counting | The sales, receipts or other movements recorded after you counted the product |
| Adjustment request | The number of the request sent to the administrator, or **No request** |

A product that was already counted within the allowed delay carries the label **Recount** next to its name.

### Movements during the count

A count takes time, and the pharmacy keeps working. The system therefore compares your figure with the stock it held when you counted the product, not with the stock at the moment you validate. In the demonstration, the stock of Carnet 2 was 60 when it was counted as 58. The assistant then recorded a delivery of 10 and it was validated before the end of the count, so the stock became 70. The result read System 60, Counted 58, Gap 2 missing and **1 movement after counting, net +10**. The delivery was not mistaken for a surplus.

The column **Movements after counting** tells you that the stock moved since your count. It is information for you and for the administrator. If many products show movements, the gaps deserve a second look before anyone trusts them.

## What happens to a gap

Every line with a gap creates one request of the type correction and sends it to the administrator. The line carries its number, such as "Request no. 2193 created". A line without a gap creates nothing. In the demonstration, the count of five products created four requests.

The request holds the quantity you counted and the stock the system held at the moment you counted. If you wrote a note, the note is the reason of the request. If not, the reason is generated from the figures and shown in the language of the screen, for example "Gap found at count no. 1123: system 83, counted 80". The administrator is notified at once.

> Important: The stock does not change when you validate. It changes only if the administrator approves the request. Until then the pharmacy keeps selling with the old figure.

### While the request is waiting

The page **Adjustment requests** is closed to your role: it is the administrator's page. You follow your requests in the tab **History**, in the card **My adjustment requests**, which lists each request with its number, the product, its outcome (Pending, Approved, Refused, Replaced by a more recent count or Cancelled) and the date. For a refused request, the reason of the administrator is written under the outcome. Nothing prevents you from starting another count meanwhile.

### When the administrator decides

The administrator approves or refuses each request separately. The details of that work are in the administrator guide. You learn the outcome in the bell.

![The decisions in the bell](figures/bell.png "small")

The first entry {1} reads "Adjustment request AJU-2196 refused (reason: Recount first: the second shelf of the back store was not included.)". The second {2} reads "Adjustment request AJU-2193 approved". The number AJU is the request number, 2196 for the request created by your count.

Approved: the stock is corrected. The administrator's request applies the difference between your figure and the system figure of that moment to the current stock, so the sales and deliveries made meanwhile stay. For Carnet 2 the stock was 70 when the request was approved, and it became 68: your 58 plus the 10 delivered after your count. A line of type **Correction** with the quantity -2 appears in **Movements**, under the name of the administrator.

Refused: nothing changes. The stock keeps its figure and the reason comes with the notice. Efferalgan stayed at 83 after the refusal above. Count the product again, with the reason in mind, and validate a new count.

Selecting the entry of an approval or a refusal in the bell opens the **Stock count** screen. Look at **My adjustment requests** in the tab **History** for the outcome, and at **Movements** to see an approved correction.

### Counting a product again

If you count again a product whose request still waits, the new count takes the place of the old request. The old request is cancelled and its outcome reads "Replaced by a more recent count", and the screen shows "Request no. 2195 replaced" under the line.

Two cases are possible. If the new figure still differs from the system, a new request is created. In the demonstration, Api1 was counted 5, then 4: request 2197 replaced request 2195. If the new figure now equals the system figure, no request is created and the old one is cancelled. Carnet 3 was recounted at 30, the system value, so request 2194 was replaced and the line read **No gap**. The administrator receives a notice "recounted Carnet 3 with no gap: request(s) no. 2194 replaced".

Only requests born from a count are replaced. A restock or correction request written by a secretary is never touched.

## Keeping every product counted

The tab **Frequency** shows which products are due. Open it before you decide what to count.

![The state of each product](figures/frequency.png)

The three tiles give the number of products **Never counted** {1}, **Overdue** {2} and **Up to date** {3}. The sentence under the title of the table gives the rule: "Each product must be counted at least every 30 days." The table lists each product with the date of its last count {5}, the days elapsed and its status {6}. The box {4} limits the table to the products that are overdue or never counted.

A product is **Never counted** if no validated count includes it. It is **Overdue** when more than the allowed number of days have passed since its last validated count, and **Up to date** otherwise. A count that was abandoned or never validated changes nothing. A product that you counted and for which the administrator refused the request is still counted as counted.

The number of days is set by the administrator, between 1 and 365, and is shown as read-only text for you. It is 30 days in the demonstration.

> Note: No message reminds you to count. The promoter and the administrator are warned by the daily check when products are never counted or overdue. Open **Frequency** at the start of each week and count first the products that are never counted.

The overdue status was not seen on the screen during the preparation of this guide, because every count in the demonstration was done the same day. It follows the rule above.

## The history

The tab **History** lists the validated counts, the most recent first.

![The history and the detail of a count](figures/history.png)

The dates **From** and **To** {1} limit the list, and [[Filter]] applies them. [[Clear filters]] removes them. Each row gives the validation date, who counted, and the summary {2}, for example "5 product(s), 4 gap(s)". Select [[View details]] {3} to open the table of that count under the list, with the columns **System** {4}, **Gap** {5}, **Movements after counting** {6} and **Adjustment request** {7}. Select [[Close]] to hide it. The list shows 50 counts per page.

In the detail of a count, the column **Adjustment request** gives the request number, for example "Request no. 2193 created", with a label that shows the outcome of that request: Pending, Approved, Refused or Replaced by a more recent count. The card **My adjustment requests**, under the list of counts, gathers the requests of all your counts. For an approved correction, **Movements** shows the line.

## Working without a connection

The count has no offline mode. Unlike the receipts of the secretary or the nurse, nothing is saved on the computer.

![The count without a connection](figures/offline.png "small")

Without a connection the card **New count** still shows, but [[Start a count]] answers "The server is not responding. Check the connection and try again.", while the yellow indicator {1} stays on the screen. The tab **Frequency** says "Unable to load the count frequency." and shows nothing. If the connection drops while you are counting, validating answers with the same sentence and the count stays open with your quantities on screen. Wait for the network and select [[Validate the count]] again, without reloading the page, because a reload empties the boxes.

## Common mistakes

**Counting from memory.** The count compares what is on the shelf. A figure copied from an old paper brings back the old error.

**Typing before looking at the whole shelf.** The time of the count is noted when you leave the box. Count first, then type, so the time is the time of the shelf.

**Leaving a box empty instead of typing 0.** An empty box means not counted, and the product stays on the list of products never counted.

**Reloading the page during a count.** The quantities are lost. Type them again.

**Validating a gap you doubt.** Once validated, the count cannot be changed and the request is sent. Recount the shelf first. If you validate anyway, count the product again later and the new count replaces the waiting request.

**Reading the notice of approval as a new count.** After an approval, the stock is already correct. Do not count the product again for that gap.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Enter a whole number between 0 and 10000000." | A box holds letters, a decimal or a negative number | Retype a whole number. |
| "Fix the invalid quantities before validating." | At least one box is wrong | Find the red line and correct it. |
| The green button is pale | No product is counted yet, or one box is wrong | Type at least one quantity. |
| "The server is not responding. Check the connection and try again." | The computer cannot reach the server | Wait for the network, then try again without reloading. |
| "Vous avez deja un comptage en cours." | You already have an open count | Reopen the screen, finish it or abandon it. |
| "Ce comptage n'est plus en cours" | The count was validated or abandoned elsewhere | Reload the page, then start a new count if needed. |
| Boxes empty after a reload | The quantities are not saved before validation | Type them again. |
| "Unable to load the count frequency." | The server cannot be reached | Reload the page when the network is back. |

## Glossary {.unnumbered}

Blind count
: A count in which the screen hides the system quantity until the count is validated.

Correction request
: The request sent to the administrator for each gap. The stock changes only if it is approved.

Gap
: The counted quantity minus the stock the system held when you counted the product. Positive means extra, negative means missing.

Never counted
: The status of a product that no validated count includes.

Overdue
: The status of a product whose last count is older than the allowed number of days.

Recount
: A new count of a product that was counted recently. A recount replaces the request still waiting for that product.

System stock
: The theoretical quantity computed by the application from receipts, sales, damage and approved corrections.
