---
title: Batches, declared outputs and shipping
role: Production manager
subtitle: Preparing a production batch, starting it, entering the results, declaring samples and other outputs, shipping the good bottles to the centre, and following the anomalies.
version: 27 October 2026
output: production-2-batches-outputs-shipping
---

## Before you start {.unnumbered}

This guide is the second one for the production manager. The first guide, "Inputs and purchases", explains how to record what is bought: the raw materials and the containers. Here you use those purchases. A production batch takes its inputs from chosen purchases, produces bottles, and ends with a shipment of good bottles to the centre. Between the two, the application keeps the count: how many bottles were expected, how many were found, how many went out as samples, and what the batch cost.

The screenshots come from a demonstration installation. The products, producers and numbers in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures. Sign-in, the language switch, the top bar, your profile and your password work as described in the first guide and are not repeated.

### The life of a batch

A batch moves through five statuses. You trigger every change yourself.

| Status | What it means | What you can do next |
|---|---|---|
| Draft | The batch is being prepared. Nothing is reserved yet. | Change the lines, save, start production, cancel. |
| In production | The inputs are taken from stock. | Enter the results, cancel. |
| Finished | The results are entered and the balance is calculated. | Declare outputs, reopen, ship, cancel. |
| Shipped | The good bottles left for the centre. | Read only. |
| Cancelled | The batch was stopped, with a reason. | Read only. |

### What the production manager can see and do

You are the only role that can create a batch, change it, start it, finish it, declare an output, ship it or cancel it. The promoter and the administrator can open the same screens and read everything, including the costs, but the server refuses every change they try to make. The assistant and the stock controller cannot open these screens at all: the server answers "access denied" to them. The administrator alone sets the two settings of the tracking screen, which are the tolerance for lost bottles and the number of days after which a batch counts as too long. You see neither of those settings, only their effect.

> Note: The costs of a batch are visible to you, to the promoter and to the administrator. They are not shown to other staff.

## The batches screen

Select **Production batches** in the menu. This is the screen the application opens on after you sign in.

![The list of batches, filtered on the status In production](figures/lots.png)

The button **New batch** {1} starts a new one. The list shows the batch number, the finished product, the production date, the good bottles and the status. A red tag **Out of tolerance** appears next to the status of a batch whose shortfall went over the limit. The column of good bottles shows a dash until the results are entered.

Three filters narrow the list. **Status** {2} keeps one status. **From** {3} and **To** {4} keep the batches whose production date falls between the two days, both included. The list updates when you change a field. Select **Clear dates** to remove the two dates. If the first date is after the second, the message "The start date must be before the end date." appears and the list is not updated. The button **Open** {5} shows the batch.

The numbers have the form FAB-2026-0004: the year and a running number, given by the application. A number is never reused, even when the batch is cancelled.

## Preparing a batch

A draft says which product you make, on which day, and which purchases you take your inputs from.

1. Select [[New batch]]. A form opens over the screen.
2. Choose the product in [[Finished product]] {1}. The list offers the products that can be made.
3. Check [[Production date]] {2}. The form proposes today.
4. Type the name of the person who runs the batch in [[Producer]] {3}. It is optional.
5. Select [[Create batch]] {4}.

![The form of a new batch](figures/new-batch.png "small")

The message "Batch created." appears and the application opens the new batch, with the status **Draft**. The product, the date and the producer cannot be changed afterwards on the screen. If one of them is wrong, cancel the draft and create another one.

### Choosing the inputs

The card **Consumptions** {1} lists what the batch takes, and the cost of each line. Below it, **Choose the purchases consumed** holds one line per purchase.

![A draft with two lines](figures/draft.png)

1. Select [[Add a line]] {5}.
2. Choose the purchase in [[Purchase]] {2}. Each choice names the input, the supplier, the delivery reference when there is one, the date and the quantity that remains, for example "Guide demo honey jars | Demo Farm Supplies | Delivery ref. BL-0412 | 26/10/2026 | Remaining 50". Only active purchases with something left are offered.
3. Type the quantity taken in [[Quantity]] {3}, in the unit of the input.
4. Repeat for every input. Select **Remove** {4} to delete a line.
5. Select [[Save]] {7}. The message "Draft saved." appears and the table of consumptions above shows the lines and the cost of the consumptions.

The rules of the lines are these.

- The batch needs exactly one line that takes a container, that is an input marked **Container** in the first guide, such as the glass bottles. The number of bottles on that line is the number of bottles you expect from the batch. A batch with no container line, or with two, cannot start.
- The container quantity must be a whole number. A quantity such as 20.5 is accepted when you save the draft, but the start is refused.
- The other inputs accept up to three decimals, with a point or a comma: 2,5 is read as 2.5. Zero is refused with the message "The quantity must be greater than zero." Letters, four decimals and a negative number are refused with "The quantity is not a valid number (3 decimals at most)."
- A purchase can appear on one line only. A second line on the same purchase is refused with "A purchase can appear only once in a batch."
- You cannot take more than what remains of the purchase. The message is "The quantity consumed exceeds what is left of the purchase." and it comes when you start the batch.
- Every line needs a purchase. A line left without one is refused with "Choose a purchase on every line."

> Tip: Two purchases of the same input from the same supplier on the same day look alike in the list. The delivery reference and the remaining quantity tell them apart. Check them against the purchase list of the first guide.

A draft can stay as long as you like. It reserves nothing, so another batch may take the same purchase before you start yours.

## Starting production

Select [[Start production]] {8}. The application saves the lines first, then starts the batch. If the saving fails, nothing starts.

The message "Batch in production, stock reserved." appears and the status becomes **In production**. At that moment the quantities leave the stock of the inputs. In the demonstration, a batch that took 20 bottles and 5 jars lowered the glass bottles from 160 to 140 and the honey jars from 220 to 215. The unit cost of every purchase is also frozen on the batch: a later purchase at another price does not change this batch.

From here the lines are fixed. If something is wrong, cancel the batch and prepare another one, as explained further on. When the production is over, select [[Finish and enter results]].

Starting is refused, with a red message at the top of the page, when the draft has no line, when the container line is missing, doubled or not a whole number, or when a purchase has less left than the batch asks. The messages are the ones listed in the rules of the lines above and in the last page of this guide.

## Entering the results

When the bottles are filled and counted, open the batch and select [[Finish and enter results]]. A form asks for the count.

![The results form](figures/finish-form.png "small")

1. Type the good bottles in [[Good bottles]] {1}.
2. Type the bottles that broke in [[Broken bottles]] {2} and the bottles you set aside in [[Rejected bottles]] {3}. Both start at 0.
3. Type the liquid that was lost in [[Liquid lost]] {4}. It is information only and does not enter the balance. It accepts up to three decimals, with a point or a comma.
4. Select [[Finish batch]] {5}.

The three bottle counts must be whole numbers, zero or more, otherwise the form says "Bottle counts must be whole numbers, zero or more." Their total cannot be higher than the number of bottles expected. If it is, the message "Le total trouve depasse l'attendu." appears and nothing is saved. This message stays in French in the English interface.

The message "Batch finished." appears and the status becomes **Finished**. The page now shows the results, the balance and the cost price.

![A shipped batch with its balance and cost](figures/shipped.png)

The **Balance** compares what you expected with what you found. **Expected** is the number of bottles on the container line. **Found** is the sum of good, broken and rejected bottles. The **Unexplained shortfall** is the difference, with its share of the expected number in per cent. In the example, 20 bottles were expected and 18 were found, so the shortfall is 2 bottles, which is 10 %. The line under the balance, "Shortfall justification" {3}, is explained in the chapter on shipping.

The **Tolerance** is the share of the expected number that the centre accepts to lose without explanation. It was 2 % in the demonstration. The batch is **Out of tolerance** {1} only when the shortfall is higher than the tolerance. A shortfall equal to the tolerance is accepted: with 50 bottles expected and 49 found, the shortfall is 1 bottle, exactly 2 %, and the batch shows **Within tolerance**. Before shipping, the card says "Current tolerance". After shipping it says "Frozen at shipping" {2}, which means that the value in force on the day of shipping stays on the batch, even if the administrator changes the setting later.

The **Cost price** card shows the **Total input cost**, which is the sum of each quantity multiplied by the unit cost of its purchase, and the **Cost per good bottle** {4}. That second figure divides the total by all the good bottles, including those you later declare as samples. In the example, 3 200 FCFA divided by 17 bottles gives 188.24, and the screen shows 188,24 FCFA, with two decimals. The liquid lost is displayed with a comma, as in "0,5", even if you typed a point.

### Correcting the results

If the count is wrong, select [[Reopen]] on the finished batch. The status goes back to **In production**, the inputs stay reserved, and you can enter the results again. The earlier counts, the balance, the cost and the **Out of tolerance** tag are cleared: they are calculated again when you finish the batch. Reopening is refused while the batch has active declared outputs: the message "Cancel the declared outputs first." asks you to cancel them first.

## Declared outputs

Not every good bottle goes to the centre. A bottle may be given as a sample to a partner, or leave the batch for another reason. The application calls this a declared output. You record it before shipping, so that the bottle does not look like a loss in the balance.

The card **Declared outputs** appears on a finished batch. It starts with a summary line {1}: "Good bottles: 17, outputs: 5, to ship: 12". The bottles **to ship** are the good bottles minus the active outputs.

![The card of declared outputs](figures/outputs.png)

1. Choose the reason in [[Reason]] {4}. **Sample** is for a bottle given as a sample. **Other** is for any unforeseen case.
2. Type the number of bottles in [[Quantity]] {5}. The label shows the most you can declare, for example "Quantity (at most 12)".
3. Type a note in [[Note]] {6}. For **Other** the note is required and the button stays grey until you write it: say what went out and why. For **Sample** the note is optional, for example where the sample goes.
4. Select [[Declare the output]] {7}.

The message "Output declared." appears and the output joins the list, with the person who declared it, the day and the time. No approval is asked: the output counts at once. The quantity must be a whole number from 1 to the number of bottles still to ship. A larger quantity is refused with "The quantity must be a whole number between 1 and 12." (the limit is the figure of the moment).

### Cancelling an output

Declared by mistake? Select **Cancel** {2} on the line of the output. A form asks for a reason. Type it and select [[Cancel the output]]. The message "Output cancelled." appears and the line stays in the list, struck through, with the tag **Cancelled** {3}, the day, and the reason. Nothing is ever deleted. The bottles go back into the quantity to ship.

An output can be declared or cancelled only while the batch is **Finished**. Once the batch is shipped, the list can no longer change.

### When all the bottles are out

If you declare every good bottle, the form disappears, the message "All bottles have gone out: nothing to ship." appears, and the button **Validate balance and ship** is greyed out. Cancel an output to be able to ship again. A batch with no good bottle at all has no shipping button either.

## Shipping to the centre

Shipping closes the batch. It creates, for the assistant and the stock controller, a production lot that follows the circuit described in their guides.

1. Open the finished batch and select [[Validate balance and ship]].
2. Choose the delivery date in [[Planned delivery date]] {1}. It is required.
3. Choose the expiry date in [[Expiry date (optional)]] {2} if the product has one.
4. If the batch is out of tolerance, a red message {3} says so, for example "Shortfall out of tolerance: 2 bottles (10 %). A justification is required." Write the explanation in [[Shortfall justification]] {4}. The button stays grey until you do.
5. Select [[Validate and ship]] {5}.

![The shipping form of a batch out of tolerance](figures/ship-form.png "small")

The first sentence of the form says how many bottles leave: "12 bottles will go to the centre as a production lot (good bottles minus declared outputs)." The message "Batch shipped to the centre." appears. The status becomes **Shipped** and a line "Production lot created" names the new lot, here LOT-20261026-005. The lot holds 12 bottles, with the delivery date and the expiry date you typed, and waits for the assistant to record its arrival. The tolerance is frozen, the justification is kept on the batch (it is the line {3} of the figure of the results), and the batch becomes read only: it has no button left.

A batch within tolerance has no justification field, and the form needs only the delivery date. In the demonstration, a batch of 48 good bottles and 1 broken bottle out of 50 was shipped that way, and its lot LOT-20261026-006 holds 48 bottles.

> Caution: A batch out of tolerance can be shipped. The shortfall is not blocked, it is explained, and the batch then appears among the anomalies that the promoter reads. Write what really happened.

## Cancelling a batch

A batch can be cancelled while it is a draft, in production or finished. A shipped batch cannot.

1. Open the batch and select **Cancel batch**.
2. Type the reason in [[Reason for cancelling]]. It is required.
3. Select [[Confirm cancellation]].

For a batch in production or finished, the form warns that "Reserved quantities will be given back to the purchase stock.", and it does. In the demonstration, a batch that had taken 10 bottles and 2 jars brought the stock from 90 to 80 bottles and from 205 to 203 jars when it started, and back to 90 and 205 when it was cancelled. The message is then "Batch cancelled, quantities given back to stock." For a draft, which reserved nothing, the message is "Batch cancelled." The reason stays on the batch.

A finished batch that still has active declared outputs cannot be cancelled. The message "Cancel the declared outputs first." asks you to cancel them first, as for the reopening.

## Tracking and anomalies

Select **Tracking and anomalies** in the menu. The screen gives the state of the whole production at a glance.

![The tracking screen](figures/suivi.png)

The tiles at the top count the batches by status, for example **In production** {1}. The tile **Anomalies** {2} counts the problems listed further down. Under the tiles, the card **Recent batches** shows the ten latest batches, with the tag **Out of tolerance** where it applies, and a button **Open** on each line.

The card **Anomalies** lists what needs a look, with an **Open** button that goes to the batch. There are four kinds.

![The card of anomalies](figures/suivi-anomalies.png)

| Kind | When it appears |
|---|---|
| Shortfall out of tolerance {1} | A batch has a shortfall above the tolerance. The line gives the bottles lost, the share in per cent and the tolerance. |
| Input below its alert threshold | An input stock fell under its threshold. This is the alert described in the first guide, which also sends a notice to your bell when the stock crosses the threshold. |
| Batch in production for too long | A batch has been in production or finished, without being shipped, for more than the set number of days, which is 7 at the moment. |
| Gap between shipped and received {2} | A shipped batch was received at the centre with a different number of good bottles. The line gives the bottles shipped, the bottles received good, and the gap. |

The demonstration shows the first and the last kinds. The kind "Batch in production for too long" could not be shown, because every batch of the demonstration is only a few hours old. The line says, in that case, "In production for 9 days, limit 7 days." for example. The shipped batch that was received short, by the assistant and the stock controller, is the sign that bottles were lost between the production site and the centre. The administrator sets the tolerance and the number of days. An anomaly disappears by itself when its cause is gone.

### Recent declared outputs

The last card lists the declared outputs of all the batches, newest first.

![The list of declared outputs](figures/suivi-outputs.png)

The filters **From** {1}, **To** and **Reason** {2} narrow it. An output declared for the reason **Other** carries the tag **To check** {3}, so that someone looks at them. A cancelled output {4} is struck through. If the two dates are in the wrong order, the message "The start date must come before the end date." appears. The list shows the 200 most recent outputs and says so with a message when it reaches that number: narrow the dates.

## Working without a connection

The batch screens read and write on the server. They keep no copy on the computer, so they need the network. The indicator at the top reads "Connected" while the server answers and "Offline" when it does not. Even then, the sentence "(your entries are saved)" does not apply to these screens.

Without a connection, the list of batches shows the red band "Could not load. Try again." and "No batches.", and the form of a new batch cannot load the products: it says "The product catalogue could not be loaded." A batch opened from a link shows the same red band and no content. None of this means the batches are gone.

If the connection drops while you send a form, the form stays open with what you typed and the message "Could not save. Try again."

Keep the form open, wait for the network, and select the button again. Then check the status of the batch on the page. A step that did not pass leaves the batch in its previous status, so nothing is half done.

> Caution: Never conclude from an empty screen that there is no batch or no stock. Reload the page once the network is back before you act.

## Common mistakes

**Choosing the wrong purchase.** Two purchases of the same input look alike in the list. The cost of the batch follows the purchase you chose. Check the remaining quantity and the supplier before you save.

**Typing a half bottle.** The container line takes whole numbers only. The draft saves the decimal and the start refuses it, so you meet the error late.

**Counting a sample as a loss.** A bottle given as a sample is a good bottle. Declare it as a sample. It then leaves the balance as an explained output and does not push the batch out of tolerance in the eyes of the promoter.

**Shipping with a vague justification.** The justification stays on the batch for good and the promoter reads it. "Counted wrongly" tells nothing. Say what happened.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Could not load. Try again." | The computer cannot reach the server | Wait for the network, then reload the page. |
| "Could not save. Try again." | The connection dropped as you sent | Keep the form open and send again when the network is back. |
| "The start date must be before the end date." | The dates of a filter are in the wrong order | Correct one of them or select Clear dates. |
| "Choose a purchase on every line." | A line of the draft has no purchase | Choose one or remove the line. |
| "The quantity is not a valid number (3 decimals at most)." | A quantity holds letters, a negative number or four decimals | Retype it with at most three decimals. |
| "A purchase can appear only once in a batch." | The same purchase is on two lines | Keep one line for that purchase. |
| "The batch must have exactly one container consumption." | No container line, or two | Keep one container line. |
| "The quantity consumed exceeds what is left of the purchase." | The purchase has less left than you typed | Lower the quantity or choose another purchase. |
| "Le total trouve depasse l'attendu." | Good, broken and rejected bottles add up to more than expected | Recount, then correct the numbers. |
| "Cancel the declared outputs first." | The batch has active declared outputs | Cancel the outputs, then reopen or cancel the batch. |
| "All bottles have gone out: nothing to ship." | Every good bottle is declared as an output | Cancel an output, or cancel the batch. |
| The button Declare the output stays grey | The reason is Other and the note is empty, or a field is empty | Fill in the reason, the quantity and the note. |
| The button Validate and ship stays grey | The delivery date is empty, or the justification is missing | Fill them in. |
| A page "Access denied" with the code 403 | The screen is closed to your role | Select the button back to your dashboard. |

## Glossary {.unnumbered}

Batch
: One production run, from the choice of inputs to the shipping of the good bottles. Its number has the form FAB-2026-0004.

Balance
: The comparison of the bottles expected, the bottles found and the unexplained shortfall.

Container line
: The line of a batch that takes a container, such as bottles. Its quantity is the number of bottles expected.

Cost per good bottle
: The total input cost of the batch divided by its good bottles.

Declared output
: A good bottle that leaves the batch before shipping, as a sample or for another reason. It is recorded with its author and its time, and it needs no approval.

Out of tolerance
: The state of a batch whose unexplained shortfall is higher than the tolerance. Shipping it needs a justification.

Production lot
: The lot created at shipping, which the assistant receives and the stock controller checks at the centre.

Shortfall
: The expected bottles minus the found bottles. It is also called the unexplained shortfall.

Tolerance
: The share of the expected bottles, in per cent, that may be missing without a justification. The administrator sets it.
