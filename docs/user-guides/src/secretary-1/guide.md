---
title: Patients, appointments and invoicing
role: Secretary
subtitle: Registering patients, finding a patient file, and recording invoices and payments at the cash desk.
version: 27 October 2026
output: secretary-1-patients-appointments-invoicing
---

## Before you start {.unnumbered}

This guide is written for the secretary at the reception desk. It covers the patient register and the cash desk, which together make up most of a working day at reception. The second secretary guide covers withdrawals and the daily cash closing.

The screenshots come from a demonstration account. Your own screens show your name and the real patients of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the secretary can see

Your menu has two groups. Under **Daily work** you find Home, Patients, Cashier, Withdrawals and Cash closing. Under **Follow-up** you find Stock, Discount history and Consultations. A Sync failures entry appears only when something you entered could not be sent to the server.

You can register patients, correct their identity details and invoice them. You do not see medical records, laboratory results or prescriptions. Those belong to the clinical staff, and the application keeps them out of the reception screens on purpose.

### Interface language

The application starts in French on a new computer. The language switch sits at the top right of every screen, next to the bell: select **EN** to work in English. The choice is kept on that computer.

> Note: A few texts stay in French in English mode, for example the code "CODE EN ATTENTE" of a patient registered offline and the yellow message "Ticket non imprimé : imprimante indisponible". This guide quotes them as they appear and gives the English meaning the first time.

## Signing in and the home screen

Each member of staff has a personal account. Never share it: every invoice and every payment records the name of the person who entered it.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}. The eye icon at the end of the field shows the password while you type.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time the server refuses new tries for a while. Wait a minute before trying again. If you have forgotten your password, use the [[Forgot your password?]] link or ask an administrator.

The home screen opens on the **Overview** page.

![The secretary home screen](figures/home.png)

The menu {1} gives access to every screen of your role. At the top right, the connection indicator {2} tells you whether the computer is in contact with the server, and the language switch {3} sets the language. The **Quick actions** row {4} opens the three forms you use most often: a new invoice, a new withdrawal and a new patient. The **Money for the period** block {5} totals what was paid, what was withdrawn and what patients still owe between the two dates shown. By default both dates are today.

The lower block lists products in critical stock. It is there so that you can warn the pharmacy before a patient asks for a product that has run out.

## Registering a new patient

Every patient who receives a service gets a file and a patient code. The code is printed on invoices and is the quickest way to find the patient again, so it must be written in the patient's notebook on the first visit.

Before you create a file, search for the patient (see chapter 3). Many people come back after months and give their name in a different order.

### Creating the file

1. In the menu, select [[Patients]], then [[Add a patient]]. The same form opens from [[Add a patient]] on the home screen.
2. Fill in the first name {1} and the family name.
3. Enter the date of birth {2}. It is required, and it is used to build the patient code.
4. If the patient carries a national identity card, type its number in [[National identity number]] {3}. Copy it from the card itself, not from memory.
5. Add a telephone number {4} and the place of residence. The phone number is what the clinical staff use to call a patient back after a result.
6. Select [[Create]] {5}.

![The new patient form, filled in for a demonstration patient](figures/patient-form.png "small")

Only the first name, the family name and the date of birth are required. The other fields can be completed later with [[Edit]] in the patient list.

The application then shows the patient code in large characters.

![The patient code shown after registration](figures/patient-code.png)

Write the code in the patient's notebook, then select [[OK]]. The [[Copy]] button puts the code on the clipboard if you need to paste it somewhere.

### The national identity number

The national identity number is optional, but it must be unique. Two patient files can never carry the same number. When a number is already used by another file, the server refuses the new patient and the application shows the message below.

![A new patient refused because the identity number is already used](figures/duplicate-rejected.png)

This is almost always the same person registered a second time, perhaps under a different spelling. Select [[OK]], search the list for the existing file and use it. The refused entry is kept under **Sync failures** in the menu. From that screen you can correct a mistyped number and send the patient again, or delete the entry when the patient already had a file.

> Caution: Do not invent or shorten an identity number to get past this message. The number exists to stop duplicate files, and a false number defeats it.

Two people with the same name and no identity number are both accepted. The application cannot tell them apart, so check the date of birth and the telephone number before you create a second "Amara Njoh".

## Finding a patient

The patient list opens with the most recent files first. The tabs above the table count the patients followed by each service: clinical care, toxicology and spiritual care. A secretary works in **All Patients** most of the time.

![Searching the patient list](figures/patient-search.png)

1. Select [[Patients]] in the menu.
2. Type part of the name or of the patient code in the search box {1}. The list narrows by itself a moment after you stop typing.
3. Check that the **All Patients** tab {2} is selected, otherwise the search is limited to one service.
4. To correct the identity details of the file, select [[Edit]] {3}.

To clear the search, empty the box.

> Note: [[Delete]] is next to [[Edit]] and is just as easy to reach. A file that already has invoices or consultations should never be deleted. If a file was created by mistake, ask an administrator.

## Appointments

Appointments are booked by the nurses and doctors from their own appointment calendar. They know how long a consultation lasts and who is on duty. The secretary account has no appointment screen.

When a patient at the desk asks for an appointment, register or find the patient first, give the patient code to the nurse on duty, and let the nurse book the slot. When the patient comes back for the appointment, the patient pays at the cash desk as described in the next chapter.

## Creating an invoice

An invoice records what the patient owes and what the patient has paid. One invoice can hold several lines: a medicine from the pharmacy, a laboratory exam, a spiritual consultation and any other service.

### Choosing the patient

1. Select [[Cashier]] in the menu, then [[New Invoice]]. The same form opens from [[New invoice]] on the home screen.
2. Type a few letters of the name or of the code in [[Search an existing patient]] {1}, then select the patient in the list that appears.
3. For a person who has no file and will not need one, for example someone who only buys a medicine, type the name in [[Walk-in patient name]] {2} instead.

![Choosing the patient of the invoice](figures/invoice-patient.png "small")

The selected patient appears in a green band with a [[Change]] button, and again in the summary on the right. The cursor then moves by itself to the scan field described in the next section.

### Scanning products

Every product of the pharmacy carries a label with an 8-digit barcode. When the patient buys a labelled product, scan the label instead of searching for the product by name.

![A scanned product: the scan field, the locked price and the product panel](figures/invoice-scan.png)

1. Select the patient. The cursor goes to the **Scan a barcode** field {1} by itself.
2. Point the scanner at the label and pull the trigger. The scanner types the code and presses Enter for you.
3. The product is added as a [[Pharmacy]] line at the catalogue price {2}. The **Selected product** panel {3} shows the photo of the product when one exists, then its name, form, dosage, price and the quantity in stock.
4. Scan the same product again to add 1 to the quantity of its line. No second line is created.
5. Scan the next product. The cursor returns to the scan field after each scan, after you add or remove a line, and after you press Enter in a quantity or price field.

If the code is not known, the window shows the message "Unknown barcode: no product matches." and no line is added. Check that the label belongs to a product of the centre, or search for the product by name. A label that cannot be read by the scanner can also be typed by hand in the same field, followed by Enter.

The panel also follows your other actions: it shows the product you have just chosen by name, and it changes to another product when you select its Pharmacy line.

The button at the top right of the window header {4} enlarges the window to the full screen, and the same button restores it. It is shown only on wide screens.

> Note: Scanning does not change prices. The scanned line carries the locked catalogue price, like a line added by name. Searching a medicine by name with the [[Pharmacy]] button still works as before.

### Adding the lines

Each coloured button adds one line {3}. [[Pharmacy]] searches the medicines in stock, [[Lab Exam]] searches the catalogue of laboratory exams and [[Spiritual Consultation]] adds a spiritual consultation. [[Free-form Service]] is for anything else: you type the description and the price yourself.

![Two invoice lines: a laboratory exam at catalogue price and a free-form service](figures/invoice-lines.png)

1. Select the button of the line type, then type a few letters in the search field of the new line and select the product or exam.
2. Change the quantity if needed.
3. Check the unit price. For a catalogue item the price {4} is filled in and locked, with the reminder "Catalog price. For another price, request a discount."
4. For a free-form service, type the unit price {5}.
5. Repeat for each line. The bin icon at the end of a line removes it.

The **Invoice total** box {6} adds up the lines as you go.

> Caution: The secretary cannot change a catalogue price. If the patient cannot pay the full price, do not use a free-form line to work around the lock: request a discount (chapter 7), so that a manager approves the reduction and it appears in the reports.

### Recording the payment

![The payment section of the invoice](figures/invoice-payment.png)

1. Choose the [[Category]] {7} that matches the main service: Consultation, Pharmacy, Hospitalization, Laboratory, Detox or Other.
2. Choose the [[Payment Method]] {8}: Cash, Orange Money, MTN Mobile Money or other mobile money.
3. Type the amount the patient hands over now in [[Initial Advance]] {9}. It cannot exceed the total. Leave 0 if the patient pays nothing today.
4. Add a short description in [[Description / Reason]] if it helps a colleague understand the invoice later.
5. Select [[Save Transaction]] {10}.

The invoice appears at the top of the cash desk list. If the advance is lower than the total, the difference shows in red in the **Balance Due** column.

### The receipt

When the centre's receipt printer is connected to the reception computer, a ticket prints by itself after the invoice is saved. When it is not, a yellow message appears at the top right: "Ticket non imprimé : imprimante indisponible" (ticket not printed, printer unavailable). The invoice is saved all the same. Once the printer is back, use [[Reprint ticket]] on the row of the invoice.

To give the patient a full A4 invoice instead, use the download button of the row and print the PDF.

## Partial payments and instalments

Many patients pay in several visits. Each payment is added to the same invoice, so the balance stays correct and the cash closing finds every amount.

![The action buttons of an invoice in the cash desk list](figures/cash-list.png)

The buttons on each row are, from left to right: view details, [[Add Payment]] {1}, [[Settle]] {2}, download the invoice, [[Reprint ticket]] {3} and cancel. Hold the mouse over a button to see its name. The **Balance Due** column {4} shows what the patient still owes. The payment buttons disappear once the balance reaches zero.

### Adding an instalment

1. Find the invoice in the list. The search box above the table and the date filters help when the list is long.
2. Select [[Add Payment]] {1} on its row.
3. Read the balance due {5} at the top of the form.
4. Type the amount received in [[Amount (XAF)]] {6}. The form proposes the full balance; replace it with the amount the patient actually gives. It cannot be more than what is still due.
5. Choose the payment method {7}.
6. Select [[Save Transaction]] {8}.

![Adding an instalment to an invoice](figures/installment.png "small")

### Settling the balance in one go

[[Settle]] {2} opens a form titled **Settle the invoice**, already filled with the whole remaining balance {1} and the payment method of the invoice. Check the amount {2} and the method {3}, then select [[Confirm settlement]] {4}. Nothing is recorded until you confirm. If the patient hands over less than the balance, replace the amount: the payment is then recorded as an ordinary instalment and the invoice stays open.

![The settlement form, filled with the remaining balance](figures/settle.png "small")

> Caution: A payment recorded by mistake cannot be removed by the secretary. Cancelling the invoice with the last button of the row asks for a written justification, and the cancellation stays visible to management. Check the patient name and the amount before you select Confirm settlement.

## Requesting a discount

Prices come from the catalogue. When a patient cannot pay the full price, the secretary asks a manager for a discount from the invoice form. The manager receives a notification, sets the reduction and approves or refuses it.

![Sending a discount request to a manager](figures/discount-request.png)

1. Prepare the invoice as usual: patient and lines.
2. Leave [[Initial Advance]] {1} at 0. A discount can only be requested on an invoice that has received no payment yet.
3. In the **Discount** section, choose the manager in [[Request a discount from]] {2}.
4. Select [[Request a discount]] {3}.

The form confirms that the request was sent and to whom. [[Save Transaction]] is now greyed out, because the invoice waits for the manager's decision.

![The invoice waiting for the manager's approval](figures/discount-pending.png)

If the chosen manager is absent, pick another name in the same list and select [[Cancel and reassign]]. Close the form with [[Cancel]] once the request is sent: the request is not lost.

In the cash desk list, a yellow banner counts the invoices awaiting approval, and the [[Status]] filter set to **Awaiting approval** lists them. Once the manager has decided, the invoice leaves the Awaiting approval filter and you record the payment with [[Add Payment]]. **Discount history** in the menu lists all your requests with their status: approved, refused or pending.

> Note: A discount request needs the connection to the server. When the computer is offline, the request cannot be sent; wait for the connection to come back.

## Working without a connection

Reception keeps working when the internet connection drops. Patients and invoices entered offline are kept on the computer and sent to the server as soon as the connection returns.

The indicator at the top right of the screen tells you where you stand.

![The indicator while the network is down, and a patient registered offline](figures/offline-code.png)

Right after you sign in, the indicator can read "Offline" for a few seconds while the copy of the data kept on the computer is prepared; it then turns to "Connected" by itself. When the connection is lost, the indicator {1} turns yellow and reads "Offline (your entries are saved)". If you register a patient or an invoice while offline, the indicator keeps reading "Offline". Your entry is saved on the computer and waits for the connection. A patient registered offline shows "Assigning the code..." {2} instead of a code, and "CODE EN ATTENTE" (code pending) in the list, because only the server can give out patient codes.

![The indicator once the connection is back](figures/online.png)

When the connection returns, the indicator goes back to green "Connected" {1} within a few seconds, the waiting entries are sent, and the patient receives a code. Give the code to the patient at the next visit, or call the patient if a result depends on it.

A few things wait for the connection: discount requests, the totals of the home screen and the counters of the patient tabs. While offline, those totals can show 0. They are not lost, they simply cannot be read from the server.

> Caution: Do not clear the browser data, uninstall the browser or switch off the computer for good while entries are waiting. Keep the computer on until the indicator shows "Connected" again.

If an entry is refused by the server once the connection is back, for example a patient whose identity number already exists, it is listed under **Sync failures** in the menu, where you can correct it or delete it.

## Common mistakes

**Creating a second file for a returning patient.** Search by family name, then by the first name, then by the telephone number before creating a file. A duplicate splits the patient's history across two files.

**Using a free-form line to change a price.** Catalogue prices are locked on purpose. Ask for a discount instead.

**Recording a payment on the wrong invoice.** Two invoices of the same patient can sit next to each other with different balances. Read the total and the date of the row before you select Add Payment or Settle.

**Confirming a settlement for more than the patient gave.** The form proposes the whole balance. If the patient paid only part of it, replace the amount before you confirm.

**Requesting a discount after taking an advance.** The request is refused once a payment exists. Ask for the discount before the patient pays.

**Logging out while entries wait to be sent.** Wait for the green "Connected" indicator before logging out at the end of the day.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Patient rejected", identity number already used | Another file already carries this national identity number | Search for the existing file and use it. Correct or delete the entry under Sync failures. |
| "Ticket non imprimé : imprimante indisponible" | The receipt printer is off or not connected | The invoice is saved. Check the printer, then use Reprint ticket. |
| Yellow "Offline" indicator | The computer cannot reach the server | Your entries are kept. Wait for "Connected"; tell the administrator if it lasts. |
| "Assigning the code..." instead of a patient code | The patient was registered offline | The code arrives when the connection is back. Note it in the notebook later. |
| Save Transaction stays grey | A required element is missing, or a discount request is pending | Check the patient and that each line has a product and a price. |
| Request a discount stays grey | No manager chosen, or an advance was entered | Choose a manager and set Initial Advance to 0. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute. Use "Forgot your password?" if needed. |

## Glossary {.unnumbered}

Balance due
: The part of an invoice not yet paid.

Catalogue price
: The price set by the administration for a product, an exam or a consultation. The secretary cannot change it.

Initial advance
: The amount paid when the invoice is created.

Instalment
: A later payment added to an existing invoice with Add Payment.

National identity number
: The number on the national identity card. Optional, but unique across all patient files.

Patient code
: The code given by the server to every patient file, for example AH2-910314NX. It is written in the patient's notebook.

Sync failures
: The screen that lists entries made offline that the server refused.

Walk-in patient
: A person invoiced by name only, without a patient file.
