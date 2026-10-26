---
title: Inputs and purchases
role: Production manager
subtitle: Recording the raw materials and containers bought for production, keeping the input stock right, correcting a mistaken purchase, and watching the alert thresholds.
version: 27 October 2026
output: production-1-inputs-purchases
---

## Before you start {.unnumbered}

This guide is for the production manager of the centre. In Glostone-Care you record what is bought to make the products of the centre: the raw materials, such as honey, and the containers, such as bottles or jars. Each purchase raises the stock of its input. Later, each production batch takes its inputs from chosen purchases, and the price of those purchases becomes the cost of the batch. The batches, the declared outputs and the shipping of finished bottles belong to the second guide for your role and are not repeated here.

The screenshots come from a demonstration installation. The inputs, suppliers and prices in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the production manager can see and do

The application opens on **Production batches**. Your menu has one group, **Production** {1}, with three screens.

![The menu of the production manager](figures/menu.png "small")

**Production batches** {2} lists the batches and belongs to the second guide. **Inputs and purchases** {3} is the subject of this guide. **Tracking and anomalies** {4} shows the count of batches by status and the list of anomalies, among them the inputs that run low.

You are the only role that can record a purchase, edit one, cancel one, create an input, edit one or deactivate one. The administrator and the promoter can read the same screens. The administrator alone sets the alert threshold of an input, and the settings of the tracking screen (the tolerance and the number of days after which a batch is reported as too long) are shown to the administrator only. The patient screens, the pharmacy stock, the cash register, the laboratory and the logs are closed to you. If you type the address of one of them, the application shows a page "Access denied" with the code 403 and a button back to your dashboard.

> Note: The prices of purchases are visible on your screens and on those of the administrator and the promoter. They are not shown to other staff.

### Signing in

Each member of staff has a personal account. Ask the administrator for yours.

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]].
3. Type your password in [[Password]].
4. Select [[Sign in]].

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again. Select **EN** in the language switch at the top right to work in English. The choice is kept on that computer.

### The top bar

The top bar shows an indicator that reads "Connected" while the server answers and "Offline" when it does not. Next to it come the bell, the language switch, the account icon and **Logout**. The bell holds your notices. For your role, the only notice is the one that tells you an input fell under its alert threshold; the chapter on the alert threshold describes it.

## The inputs and purchases screen

![The screen Inputs and purchases](figures/screen.png)

The screen has two parts. The card **Input stock** lists every active input with its unit, the **Remaining stock** {3}, the **Alert threshold** {4} and the **State** {5}. The checkbox **Show deactivated** {2} adds the inputs that were put aside. A container carries a blue **Container** tag next to its name. The button **New purchase** {1} opens the purchase form.

The card **Input purchases** {7} lists every purchase with its supplier, delivery reference, date, quantity, unit cost, the quantity that remains and its status. The newest purchases come first. Active purchases carry the button **Cancel purchase** {8}. The buttons at the end of an input row, such as **Deactivate** {6}, are explained further on.

The stock of an input is the sum of the **Remaining** quantities of its active purchases. The remaining quantity of a purchase is what no batch has taken yet. With 50 jars of honey bought and none used, the purchase shows 50 remaining. When a batch takes 30 of them, it shows 20, and the stock of the input falls by 30.

## Recording a purchase

A purchase is one delivery of one input from one supplier at one price. Record it when the goods arrive, with the delivery note in your hand.

### An input that already exists

1. Select [[New purchase]]. A form opens over the screen.
2. Keep **Existing input** selected {1}.
3. Choose the input in [[Input]] {2}. The list shows the name and the unit, for example "Guide demo honey jars (jar)", and offers active inputs only.
4. Type the supplier in [[Supplier]] {3} and the number of the delivery note in [[Delivery reference]] {4}. Both are optional, and both are worth filling in, because they are the only way to find the delivery again.
5. Check [[Purchase date]] {5}. The form proposes today. Change it when you record an older delivery.
6. Type the quantity in [[Quantity]] {6}, in the unit of the input, and the price of one unit in [[Unit cost (FCFA)]] {7}.
7. Select [[Save]] {8}.

![The purchase form](figures/buy-form.png)

The message "Purchase saved." appears for a few seconds. The stock of the input rises by the quantity bought {1}, and the purchase takes the first row of the list, with its delivery reference {2} and its unit cost {3}. In the example, the stock of honey jars went from 170 to 220 after a purchase of 50.

![After the purchase](figures/buy-saved.png)

The browser refuses to send the form while a required field is empty, a quantity is zero or the cost is negative, and it marks the field. Quantities accept up to three decimals, which suits a liquid bought in litres. The unit cost accepts two.

### An input that does not exist yet

An input is created at the moment of its first purchase. There is no separate screen to create one.

1. Select [[New purchase]], then **New input** {1}.
2. Type the name of the input in [[Input name]] {2} and its unit in [[Unit (for example L, kg, piece)]] {3}. Use the same unit on the delivery note and in the form, because the stock is counted in it.
3. Select the checkbox **This is a container** {4} if the input is a bottle or a jar that holds the finished product. Leave it empty for raw materials and small supplies such as stoppers.
4. Fill in the supplier, the delivery reference, the date, the quantity {5} and the unit cost {6} as for an existing input.
5. Select [[Save]].

![A purchase of a new input](figures/new-input-form.png)

The new input appears in the stock card at once, with the quantity bought. Choose the container tag with care. The batch form accepts exactly one container line, in whole units, and the tag is what tells the application which input that line may take.

## What the price of a purchase becomes

An input has no price of its own. The price lives on each purchase, and two purchases of the same input can have two prices. When you prepare a batch, you choose which purchases it takes and in what quantity. The cost of the batch is the sum, for each line, of the quantity taken multiplied by the unit cost of that purchase. The list you choose from names the input, the supplier, the date and the quantity that remains of each active purchase. A cancelled purchase is not offered.

This has two consequences for the work of recording. A wrong unit cost distorts the cost price of every batch that takes that purchase. You can still correct the cost of a purchase that no batch has taken, as the next chapter explains. Check the price against the delivery note before you select **Save**. And type the unit cost, not the total of the invoice: 400 stoppers invoiced 8 000 FCFA are recorded as a quantity of 400 and a unit cost of 20.

## Correcting a mistaken purchase

Two corrections exist. A purchase that no batch has taken can be edited: the supplier, the delivery reference and the unit cost change, the quantity does not. For any other mistake, cancel the purchase with a reason and record it again.

### Editing a purchase

1. In the list of purchases, select [[Edit purchase]] on the line. The button appears only on an active purchase that no batch has taken.
2. Change the supplier, the delivery reference or the unit cost in the form **Edit a purchase**. The unit cost is required.
3. Select [[Save]].

The message "Purchase updated." appears. If a batch took part of the purchase in the meantime, the server refuses the change and shows its message in the form.

### Cancelling a purchase

1. In the list of purchases, select [[Cancel purchase]] on the wrong line.
2. Type the reason in [[Reason for cancelling]] {1}. It is required.
3. Select [[Confirm cancellation]] {2}.

![The cancellation form](figures/cancel-form.png "small")

The message "Purchase cancelled." appears, the line shows the status **Cancelled** and has no button left, and the stock of the input falls by what that purchase held. An input that then has no active purchase shows the button **Edit** again. A cancelled line keeps its original quantity and shows 0 in the **Remaining** column.

When a batch has already taken part of a purchase, the cancellation is refused with a red message {2} in the form.

![A refused cancellation](figures/cancel-refused.png "small")

The message is "This purchase has already been consumed by a batch." It means that the purchase has been used, and that its price is already part of a batch. Close the form. The purchase stays as it is.

> Caution: Cancel only to correct a recording mistake. If goods were bought and a part of them was later damaged or lost, the purchase stays as it is. The loss belongs to the batch that used the goods.

## Editing and deactivating an input

An input that has no active purchase can be edited, and an input that was bought and used is locked. The end of each row tells you which case you are in. Right after a first purchase the row reads "Locked: already used". If you cancel that only purchase before any batch uses it, the input becomes editable again, with the button **Edit**.

1. Select [[Edit]] on the row.
2. Correct the name {1}, the unit {2} or the container tag {3}.
3. Select [[Save]] {4}.

![Editing an input](figures/edit-input.png "small")

"Input updated." confirms the change. On a locked input the name, the unit and the type can no longer be changed, because purchases and batches rely on them. The only action left is to deactivate it.

To put aside an input that is no longer bought, select [[Deactivate]] on its row and confirm. The input leaves the stock card and the purchase form, no new purchase can be recorded for it, and its stock and history are kept. Select **Show deactivated** {1} to see it again, with the tag **Deactivated** {2}. The button **Reactivate** {3} brings it back.

![A deactivated input](figures/inactive.png)

## The alert threshold

Each input has an **Alert threshold**, in its own unit. When the remaining stock falls under it, the figure of the stock turns red and the state reads **Below threshold** {2}, in place of **Stock sufficient** {3}. A new input starts with a threshold of 0, which never raises an alert.

![An input below its threshold](figures/alert.png)

You cannot change a threshold. Ask the administrator, who sets it with a button **Set threshold** on the same screen, and give the number: the stock under which you want to be warned, that is the quantity needed to cover the next batches while the supplier delivers. In the example the administrator set 300 {1} for the honey jars, which stood at 220.

The same alert appears on **Tracking and anomalies**. The tile **Anomalies** {1} at the top counts it, together with the other anomalies of the batches, and the list below shows the line "Input below its alert threshold" {2}, the name of the input and the text "Stock 220 jar, threshold 300 jar." {3}.

![The alert on the tracking screen](figures/suivi-alert.png)

The alert disappears by itself once a purchase brings the stock back above the threshold.

### The notice in the bell

When the stock of an active input falls under its threshold, you receive a notice in the bell: "Input [name] is below its alert threshold: [stock] [unit] (threshold [threshold])." The administrator and the promoter receive it too. The notice is sent once each time the stock crosses the threshold: starting a batch that takes the stock under the line, cancelling or editing a purchase, or a new threshold set above the stock. It is not repeated while the stock stays under the threshold. Selecting the notice opens **Inputs and purchases**. The daily check that the promoter reads also lists an input that stands under its threshold.

## Finding a purchase again

The two fields **From** and **To** above the list of purchases keep only the purchases whose date falls between the two days, both included. The list updates when you change a field. Select **Clear dates** to see all of them again.

If the first date is after the second, the message "The start date must be before the end date." appears and the list is not updated. Correct one of the dates. The filter acts on the list of purchases only. The stock card always shows the current stock.

## Working without a connection

The screens of this guide read and write on the server. They keep no copy on the computer, whatever the top indicator says: for your role, the sentence "Offline (your entries are saved)" does not apply to these screens.

When the computer cannot reach the server, the screen shows the red band "Could not load. Try again.", the stock card says "No input recorded." and the list says "No purchase recorded." This does not mean that nothing is in store. If you fill in a purchase and select **Save** without a connection, the form answers "Could not save. Try again." {1} and keeps what you typed.

![A purchase without a connection](figures/offline.png)

> Caution: Never conclude from an empty screen that there is no stock. Reload the page once the network is back before you act. Keep the form open and select **Save** again when the connection returns, and check the list afterwards to be sure the purchase was recorded only once.

## Your profile and password

The account icon at the top right opens **My Account**. On the **Profile** tab, correct the full name, the e-mail address or the phone number, then select [[Save]]. The user name and the role cannot be changed here. The **Password** tab takes the current password and the new one, which has at least 8 characters. Select **Logout** at the end of the day, mostly on a computer that other people use.

## Common mistakes

**Typing the invoice total as the unit cost.** The stock is right and the cost of every batch is far too high. Divide the total by the quantity before you type.

**Mixing units.** A purchase of 5 boxes of 50 stoppers is 250 pieces if the unit of the input is "piece". Convert on the delivery note before you type.

**Creating the same input twice.** "Honey jar" and "Honey jars" are two inputs with two stocks. Open the list of the form and look before you choose **New input**. The name and the unit of an input that was used can no longer be changed.

**Ticking the container box by habit.** It decides which input the container line of a batch may take, and it is locked after the first use.

**Cancelling to hide a loss.** A cancellation is meant for a recording mistake. It asks for a reason, and it is refused once a batch has used the goods.

**Ignoring the bell.** The notice of an input under its threshold comes once. Read the state column before you start a batch.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| A page "Access denied" with the code 403 | The screen is closed to your role | Select the button back to your dashboard. |
| "Could not load. Try again." and empty lists | The computer cannot reach the server | Wait for the network, then reload the page. |
| "Could not save. Try again." | The connection dropped as you sent | Keep the form open and select Save again when the network is back. |
| "This purchase has already been consumed by a batch." | A batch used that purchase | Leave the purchase as it is. Tell the administrator if the price was wrong. |
| No Edit purchase button on a line | The purchase is cancelled, or a batch took part of it | The cost can no longer change. Tell the administrator if the price was wrong. |
| "The reason is required." | The cancellation was sent without a reason | Type the reason, then confirm. |
| "The start date must be before the end date." | The two dates of the filter are in the wrong order | Correct one of them, or select Clear dates. |
| The input is missing from the purchase list | The input is deactivated | Select Show deactivated, then Reactivate. |
| No Edit button on an input | A purchase has already been recorded and used | The name, unit and type are locked. Deactivate it if it must go. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Alert threshold
: The stock of an input under which the screen shows a warning. Only the administrator sets it.

Container
: An input that holds the finished product, such as a bottle or a jar. A batch takes one container line.

Delivery reference
: The number on the delivery note of the supplier. It identifies the purchase.

Input
: A raw material, a container or a small supply bought for production. The stock of an input is counted in its unit.

Purchase
: One delivery of one input, with its quantity, its unit cost, its supplier and its date.

Remaining
: The part of a purchase that no batch has taken yet. The stock of an input is the sum of the remaining quantities of its active purchases.

Unit cost
: The price of one unit of the input, in FCFA, as invoiced by the supplier.
