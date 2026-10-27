---
title: Getting started, accounts, catalogue and prices
role: Administrator
subtitle: Signing in, creating and managing staff accounts, and keeping the exam and product catalogue and its prices correct.
version: 28 October 2026
output: admin-1-getting-started-accounts-catalogue
---

## Before you start {.unnumbered}

This is the first guide for the administrator. It covers what you do to get the centre running and to keep its reference data right: your own sign-in, the staff accounts, and the catalogue of laboratory exams and pharmacy products with their prices. The second guide covers oversight: discount approvals, the cash register set-up, the organisation settings and the logs.

The screenshots come from a demonstration account. Your screens show your own name and the real data of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures. The test accounts and test records used for the figures were deleted afterwards.

### What the administrator can do

The administrator account opens every screen of the application. The menu on the left lists them: Dashboard, Toxicology, Laboratory, Financial Management, discount screens, Cash closings, Reports, Users, Patients, Stock management, Lab stock, Production, Audit and Security, and System Configuration. A few entries that belong to other roles' daily work, such as the stock reception queue, are hidden from your menu on purpose.

This guide uses three of them: **Users**, **System Configuration** and **Stock management**, plus the **Config** tab of the **Laboratory** screen. For the others, see the second guide.

### Interface language

The application starts in French on a new computer. Select **EN** at the top right of any screen to work in English. The choice is kept on that computer.

> Note: A few labels stay in French in the English interface, for example the role names in the account form ("Médecin", "Infirmier(e)"). This guide quotes the label exactly as it appears on screen and gives its meaning the first time.

### Connection

Staff who work at the reception and cash desk can keep entering data when the network drops. Your administration screens are different: creating accounts and changing prices needs the server. If a save fails, check your connection first.

## Signing in and the home screen

Each person has a personal account, and your account is the most powerful one. Never share it, and sign out when you leave the computer.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in Chrome or Edge.
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}. The eye icon shows the password while you type.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time the server refuses new tries for a while. Wait a minute before trying again.

The home screen opens on the **Overview** page.

![The administrator home screen](figures/home.png)

The menu {1} gives access to every screen. **Users** is the entry for staff accounts, and **System Configuration** {2} is at the bottom of the menu: scroll the menu if you do not see it. The language switch {3} sets the language. The account icon {4} opens your own profile and password form (see the chapter on accounts). **Quick actions** {5} offers shortcuts, among them **Manage Staff**, which opens the same staff list as **Users**.

The figures of the overview, such as revenue, withdrawals and cash balance, cover the dates in **Start Date** and **End Date**. By default both are today. Reading those figures belongs to the second guide.

## Staff accounts

Every member of staff needs an account before they can sign in, and the role of the account decides what they see. You create the accounts, change them, and switch them off when someone leaves.

![The staff list, filtered on test accounts](figures/users-list.png)

Select [[Users]] in the menu. The list shows one row per account. The search box {1} looks in names, e-mail addresses and roles. [[New Account]] {2} opens the creation form. The **Role** column {3} shows a coloured label, and the **Status** column {4} shows **Active** or **Inactive**. The pencil button {5} edits an account and the red button {6} deletes it.

The **Role** column shows the role of the account under its stored name, for example "medecin" or "nurse". Under it the row shows the specialty of a doctor, or the security group for the other roles, and the words "Head nurse" for a head nurse. A few older accounts may still show "N/A": open them with the pencil button to see and set the role.

### Creating an account

1. Select [[New Account]].
2. Type the first name {1} and the last name. The application builds the full name from both.
3. Choose a user name {2}. It must be unique, and the person types it at every sign-in. A simple pattern such as first initial and family name avoids mistakes.
4. Type the e-mail address, which must look like a real address, and a phone number if you have one.
5. Type a first password in [[Password]] {3}. Use the eye icon to check what you typed. The form does not check the length, so choose a password of at least 8 characters, because the person will need that length to change it later.
6. Choose the **Security Group** {4}, then the [[Role]] {5}. The list of roles depends on the group (see the table below).
7. Leave [[Active account (allowed to log in)]] {6} ticked.
8. Select [[Create Account]] {7}.

![The new account form for a secretary](figures/user-form.png "small")

The new account appears in the list. If the user name is already taken, the form stays open and a red message explains that the server refused the save; choose another user name and save again. Give the user name and the first password to the person yourself, and ask them to change the password at their first sign-in.

| Security Group | Roles offered |
|---|---|
| Administration & Management | Administrateur, Promoteur, Assistant, Responsable de production, Contrôleur de stock, Psychologue, Conseiller Spirituel, Resp. Toxicomanie |
| Medical Service | Médecin, Infirmier(e) |
| Secretariat | Secrétaire |
| Laboratory | Laborantin |

The group is chosen first, and changing it clears the role. Pick the group that matches the person's job, then the role.

### Doctors and head nurses

Two roles show an extra field once you choose them.

For a **Médecin**, a **Specialty** list appears and is required. For an **Infirmier(e)**, a [[Head nurse]] box appears.

![The head nurse box, shown for a nurse](figures/user-headnurse.png "small")

Tick [[Head nurse]] {2} (and choose [[Role]] {1}) for the nurse who organises the others. The head nurse is still a nurse for every other purpose. The difference is that the head nurse, like a doctor, can change the nurses' duty schedule. An ordinary nurse can only read it. The box exists only on the nurse role: choosing another role clears it.

### Psychologist accounts

A **Psychologue** account shows one more box, [[Sees only their own toxicology patients]]. It is off by default, so a new psychologist sees every patient followed in toxicology, as before. Tick the box, when you create the account or later in the edit form, for a psychologist who must see only the patients they currently follow. The effect is limited to the toxicology screens:

- The lists of active and discharged patients and the patient files show only the patients whose current psychologist is that person.
- The dashboard figures are personal: the tiles count only those patients, and the split by psychologist is hidden.
- A **Previously followed patients** tab shows the patients that were transferred to a colleague. They open in reading mode only.

The box exists only on the Psychologue role: choosing another role clears it. The server applies the change at once. The tab appears the next time the person opens Toxicology Monitoring.

As administrator you can also move a patient from one psychologist to another with the [[Transfer]] button of Toxicology Monitoring. The procedure is in the guide "Toxicology manager 2".

### Changing an account

Select the pencil button of the row. The same form opens with the current values.

![The edit form of a head nurse account](figures/user-edit.png "small")

1. Change the name, e-mail address, phone, role or head nurse box as needed {3}{4}.
2. To give the person a new password, type it in the password field next to the eye icon {2}. The label reads "New password (optional)". Leave it empty to keep the current one.
3. Select [[Update]] {6}.

The user name {1} is read-only in this form: it is greyed out and cannot be typed over. If a user name is wrong, create a new account and deactivate the old one.

### Resetting a forgotten password

There is no reset link by e-mail. On the sign-in screen, the link [[Forgot your password?]] only shows a message asking the person to contact the administration. When someone forgets a password, open their account, type a new password as described above and give it to them in person. They can then change it themselves (see the next section).

### Switching an account off

Untick [[Active account (allowed to log in)]] {5} in the edit form and select [[Update]]. The row now reads **Inactive** in the **Status** column.

The person can no longer sign in, and their name, invoices and records stay in the system. Tick the box again to bring the account back.

The sign-in screen does not tell the person that the account is switched off. It shows the same message as for a wrong password, on purpose, so that nobody can find out which user names exist. The real reason is written in the sign-in log, which you can read in the Audit and Security screen (see the second guide).

![The message shown for an inactive account and for a wrong password](figures/login-refused.png "small")

If someone reports "Incorrect username or password" when you know the password is right, look at the **Status** column first.

### Deleting an account

The red button asks "Do you really want to delete" followed by the person's name, and then removes the account for good. Use it only for an account created by mistake and never used. For a person who has left, switch the account off instead: a deleted account cannot be recovered, and the server may refuse to delete an account that already appears in invoices or records. When it refuses, a red message reads "Deletion failed." Creating, changing and deleting an account are all written in the audit log.

### Your own profile and password

Every user, you included, can correct their own details and change their own password from the account icon at the top right.

1. Select the account icon.
2. On the **Profile** tab, the first one, change the full name, e-mail address or phone number.
3. Select [[Save]]. A green message confirms that the profile is updated.

The user name and the role cannot be changed here.

![The password tab, after a wrong current password](figures/account-password.png "small")

1. Open the **Password** tab, the second tab of the form.
2. Type the current password {1}, then the new one twice {2}{3}. The new password must have at least 8 characters, and both entries must match.
3. Select [[Save]] {4}.

If the current password is wrong, the form answers "The password you entered is incorrect." {5}. When the change succeeds, the application signs the person out of every session, including the one in use, and asks for a new sign-in with the new password.

> Tip: After you reset someone's password, ask them to sign in at once and change it. Only they should know the final password.

## Prices and the catalogue

Every priced item in the centre comes from a catalogue that you maintain: the laboratory exams and the pharmacy products. The cash desk reads these prices when it builds an invoice, and what you enter here is what patients are charged.

### How the price lock works

The secretary cannot type a price for a catalogue item. The invoice form fills the unit price from the catalogue and makes the field read-only. Only the administrator and the promoter can type any price.

![A secretary's invoice with a locked price, an undefined price and a free line](figures/price-lock.png)

The figure shows three lines of a secretary's invoice. Line 1 is an exam priced at 8 000 FCFA. Its price field {1} is grey and carries the note "Catalog price. For another price, request a discount." Line 2 is an exam whose catalogue price is 0 {2}: the form shows "Price not defined, contact the administrator." and the invoice cannot be saved. Line 3 is a free-form service {3}, whose price the secretary types.

The rule depends on the type of line.

| Line type | Where the price comes from | Can the secretary change it |
|---|---|---|
| Pharmacy product | Product price in Stock management | No |
| Laboratory exam | Exam price in System Configuration | No |
| Family restoration consultation | Amount recorded on the consultation | No |
| Free-form service | Typed at the cash desk | Yes |
| Spiritual consultation | No tariff | Yes |

A price of 0 or an empty price means "not defined": the sale is refused until you set a price. When a patient or a doctor asks for a different price, the secretary uses the [[Request a discount]] button of the invoice, and the promoter or you decide in the discount screens (second guide).

The same lock applies on the server, so a secretary cannot get round it by sending the data another way. One exception exists for invoices entered while the cash desk was offline: they are accepted when the connection returns even if the price has changed in between, and the difference is recorded and reported to you and the promoter as a notification and in the Reports.

> Important: Many exams have no price yet. In the demonstration data, 45 of the 52 exams have a price of 0. A secretary cannot invoice any of them until you set its price. Check the whole list before the centre opens.

### Exam prices

Exam prices are set in **System Configuration**, in the section **Exam Pricing**.

![The exam pricing list](figures/exam-list.png)

1. Select [[System Configuration]] at the bottom of the menu. The section **Organisation identity and document header** is open at the top: scroll down to **Exam Pricing**.
2. Use the search box {1} to find an exam by code, name or category.
3. Read the price in the **Price (FCFA)** column {3}.

To add an exam:

![The new exam form](figures/exam-form.png "small")

1. Select [[New Exam]] {2} in the list.
2. Type the exam name {1} and a short code {2}. The code is the permanent identifier of the exam: it cannot be changed afterwards, and it must be unique.
3. Type the category {3} as free text. Reuse the spelling of the existing categories, such as Biochimie or Serologie, because the category is a text and not a list. A different spelling creates a new category.
4. Type the price in FCFA {4}.
5. Select [[Save]] {5}.

The price must be a multiple of 100: the browser refuses a value such as 7550 with a message about the nearest valid values. For an exam that costs a different amount, round it to the next hundred.

If the code already exists, the application answers "Le code 'DEMO_TEST' existe déjà." in a pop-up window, and nothing is saved.

To change a price, select [[Edit]] on the row, the first of the two buttons.

The edit form is the same as the creation form, but the code is greyed out, with the note "The code cannot be changed after creation." Type the new price and select [[Save]]. The new price applies to every invoice line created from then on. A secretary who already has an invoice form open must close and reopen it to see the new price. Invoices already saved keep the price they were saved with.

The red [[Delete]] button {5} on the list removes an exam after a confirmation. The confirmation window asks "Delete this item?". Delete only an exam created by mistake: a deleted exam disappears from the cash desk and from the laboratory, and requests that already used it can no longer refer to it.

### The laboratory catalogue

The **Laboratory** screen has its own list of exams, on the **Config** tab.

![The exam catalogue in the Laboratory screen](figures/lab-catalog.png)

Select [[Laboratory]] in the menu, then **Config** {1}. The page is titled **Exam Catalog** and lists the code, the name, the category and the price of each exam. [[New Exam]] {2} opens the same form as in System Configuration. Each row has three buttons: **Edit exam**, which opens the same form with the code greyed out, **Parameters** (see the next section) and the red **Delete** {4}, which asks "Delete the exam ... ? This cannot be undone." before it removes the exam.

### Exam parameters

An exam is made of parameters, the lines the laboratory technician fills in when entering a result: a name, a unit, the type of value (number or text), and the normal ranges. The technician sees them on the **Bench** tab when a request for the exam is open, and a result is only complete once the values are entered.

You manage the parameters yourself. In the **Exam Catalog**, select **Parameters** on the row of the exam. A panel titled "Parameters of exam" followed by the exam name opens. If the exam has none yet, it reads "No parameter for this exam."

![The parameters panel of an exam, with a normal range and the order arrows](figures/exam-parameters.png)

1. To add a parameter, fill the block at the bottom of the panel: **Parameter name**, **Unit** and **Result type** (**Number** or **Text**), then select [[Save]]. The name field is {1} and the button is {2}.
2. To change a parameter, select **Edit** on its card. The block at the bottom is filled with its values; change them and select [[Save]].
3. To add a normal range to a parameter, use the line under **Reference ranges** on its card. Choose **Any**, **Male** or **Female** {3}, type **Min age** and **Max age**, then **Min value** and **Max value**, and select **Add range** {4}. A range can be removed with its small red bin. The laboratory judges a value against the range of the patient's sex, so give separate ranges for men and women when they differ.
4. To delete a parameter, select the red **Delete** button of its card and confirm "Delete this parameter?".

The up and down arrows {5} on each card set the order in which the parameters appear on the bench, in the result and on the printed sheet. Select the arrow to move a parameter one place. The order is kept for everyone.

> Caution: Deleting an exam that already has parameters can be refused by the server with an error message. If that happens, delete its parameters first, one by one.

Define the parameters of a new exam before you announce it to the laboratory: until then, the bench shows "No parameter configured or recorded for this exam."

### Pharmacy products

Pharmacy and natural products, and medical supplies, are managed in **Stock management**.

![The product list in Stock management](figures/stock-list.png)

Select [[Stock management]] in the menu, then the entry of the same name in the sub-menu. The search box {1} and the category filter {2} narrow the list. The **Unit Price** column {4} holds the selling price that the cash desk uses. [[New Product]] {3} adds a product. For each row, [[Edit]] {5} changes the product and [[Delete]] {6} removes it.

To add a product:

![The new product form](figures/product-form.png "small")

1. Select [[New Product]].
2. Type the name {1} and choose the category {2}: **Pharmaceutical**, **Natural / Traditional**, **Medical Equipment** or **Other**.
3. Type the selling price in FCFA {3}.
4. For a pharmaceutical product, choose the form (Tablet, Syrup, Injection and so on). You can also type a dosage, a number such as 500 (the label reads "Dosage (mg/ml)").
5. In the stock section, type the starting quantity {4} and the alert threshold {5}, the quantity under which the product is flagged as low (the field is labelled "Alert Threshold (Min)").
6. Type the expiry date {6}. For medical equipment that does not expire, the form says "Optional for non-perishable equipment." and you can leave it empty.
7. Select [[Save]].

> Note: The dosage you type is kept and shown again when you reopen the product. If the server refuses a save, a message explains why instead of a technical text.

The quantity can be typed here only because you are an administrator. Other roles cannot set a quantity: stock enters through a reception checked by the stock controller, and later quantities change through sales and counts. Use the quantity field for the opening stock of a new product, and prefer a reception afterwards, so that the movement is traced.

To change a price, select [[Edit]] on the row.

![Editing a product](figures/product-edit.png "small")

Type the new price {1} and select the confirmation button {3}, which reads "Update". The quantity {2} shows the current stock and stays editable for you. After the save, the list shows the new price, and the cash desk uses it for the next invoice.

The red [[Delete]] button removes a product after a confirmation. For a product that is no longer sold, a price of 0 stops sales, because the cash desk then refuses it as "Price not defined", while the history stays intact.

> Tip: A product or an exam with a price of 0 is the standard way to take an item out of sale without losing its history.

### What to check when prices change

When the promoter agrees a new tariff, update the list in one session, exam by exam and product by product, then open an invoice form with a secretary account to confirm the new price is the one shown. If a notification arrives about a price that differs from the catalogue, an invoice was entered offline before the change; it needs no action beyond reading it.

## Common mistakes

**Choosing the wrong security group.** The role list depends on the group. If a role is missing from the list, the group is wrong.

**Leaving the first password in circulation.** Change it with the person at their first sign-in, or ask them to change it from their own profile.

**Deleting an account instead of switching it off.** A deleted account cannot be recovered and may break the history of invoices. Untick the active box.

**Trusting the Role column for old accounts.** A few older accounts show "N/A". Open the account to check the role, the specialty or the head nurse box.

**Ticking the own-patients box on the wrong person.** A psychologist with the box ticked loses sight of the other patients of the service. Untick it in the edit form to give the full view back.

**Forgetting that the user name cannot change.** The field is read-only in the edit form.

**Typing an exam price that is not a multiple of 100.** The form refuses it. Round it.

**Leaving a price at 0.** The item cannot be sold. Check the whole catalogue before opening to patients.

**Creating an exam without its parameters.** A new exam has no parameters until you add them in the Parameters panel, so the technician cannot enter a result.

**Reusing a category with a different spelling.** Categories are free text, so "Biochimie" and "biochimie" are two categories.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Incorrect username or password" for a person who types the right password | The account may be inactive, or the password was reset | Check the Status column, then reset the password. |
| A new account does not appear, the form stays open and a red message appears | The server refused the save, most often because the user name is already used | Search the list for the name, then choose another user name. |
| The role list is empty or does not offer the role | The security group does not match | Change the group first. |
| A pop-up "Le code ... existe déjà." | The exam code is already used | Choose another code. |
| "Please enter a valid value. The two nearest valid values are ..." on an exam price | The price is not a multiple of 100 | Round the price. |
| "Price not defined, contact the administrator." at the cash desk | The catalogue price is 0 or empty | Set the price in System Configuration or Stock management. |
| "Catalog price. For another price, request a discount." | The price is locked for the secretary | Use the discount request, or change the catalogue price. |
| "The password you entered is incorrect." | The current password typed in the profile form is wrong | Retype it, or reset the password from the account form. |
| Signed out right after changing a password | This is normal after a password change | Sign in again with the new password. |
| The technician sees "No parameter configured or recorded for this exam." | The exam has no parameters | Add them with the Parameters button of the Exam Catalog. |

## Glossary {.unnumbered}

Active account
: An account that is allowed to sign in. An inactive account keeps its history but cannot connect.

Catalogue
: The list of priced items the cash desk can sell: laboratory exams and pharmacy products.

Catalogue price
: The price stored on an exam or a product. For a secretary it is the only price allowed.

Exam parameter
: One line of a laboratory result, with a name, a unit, a type of value and normal ranges.

Head nurse
: A nurse who is allowed to change the duty schedule of the nurses, like a doctor.

Previously followed patients
: A tab of a limited psychologist that lists the patients who were transferred to a colleague. They open in reading mode.

Price not defined
: A catalogue price of 0 or empty. The item cannot be invoiced by a secretary.

Role
: The job of an account, which decides the screens and actions it has.

Security group
: The family of roles an account belongs to: administration, medical, secretariat or laboratory.
