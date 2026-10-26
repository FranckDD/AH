---
title: Shifts and hospitalisation
role: Nurse and head nurse
subtitle: Reading the shift calendar, planning the rotation as head nurse, and following the patients who stay in the centre, from the admission to the discharge letter.
version: 27 October 2026
output: nurse-2-shifts-hospitalisation
---

## Before you start {.unnumbered}

This is the second guide for nurses. The first one covers signing in, triage, consultations, appointments, laboratory results, the notification bell, the offline mode and your profile. None of it is repeated here. This guide covers two subjects: the Nurse Schedule, which shows who is on duty, and the care of the patients who are hospitalised.

The screenshots come from a demonstration installation, and the patients and nurses in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What a head nurse is

A head nurse is an ordinary nurse account with one extra right: editing the rotation. The right is given by an administrator, who ticks the box "Head nurse" in the user form. There is no other difference. A head nurse has the same menu, the same patient screens and the same hospitalisation screens as every other nurse, and a doctor can also edit the rotation.

| | Nurse | Head nurse | Doctor |
|---|---|---|---|
| Read the Nurse Schedule | Yes | Yes | Yes |
| Add or remove a nurse on a shift | No | Yes | Yes |
| Admit, follow, discharge a patient | Yes | Yes | Yes |
| Download the discharge letter | Yes | Yes | Yes |

The nurse and the head nurse columns of the second part were checked with the demonstration accounts. The doctor column comes from the access rules of the application and was not tried with the doctor account for the schedule.

### Interface language

All labels in this guide are the English labels, selected with **EN** at the top right. Three things stay in French whatever the language: the discharge letter, the error messages under the Hospitalization card, and the message shown when the server refuses a schedule change because your account may not edit the rotation. The refusals that come from the shift rules (chapter 2) are shown in the language of the screen.

## The shift calendar

The Nurse Schedule shows, for each day, which nurses work in the morning, in the afternoon and at night. Every nurse can read it. It is the only place where the rotation is written down, so look at it at the start of each week.

Select **Nurse Schedule** in the menu, under **Activity**.

![The schedule of the week, read by a nurse](figures/plan-nurse.png)

The screen opens on the current week, from Monday to Sunday. Today carries a blue "Today" label and a green frame. Each row is a day, and the three columns are Morning, Afternoon and Night. A dash means that nobody is assigned to that shift. The names are the full names of the accounts, one under the other when several nurses share a shift. On Wednesday 28 October, for example, two nurses work in the morning.

You find your own shifts by reading for your name {3}. The screen does not highlight it and has no filter by nurse. If several nurses have similar names, check the spelling against your account name at the top of the screen.

1. Use the arrows on each side of the dates to move to the previous or the next week.
2. Select [[Today]] to come back to the current week from any other period.
3. Select [[Month]] {1} to see the whole month, and [[Week]] to come back.
4. Select a day to open its panel on the right, titled "Schedule for" followed by the date {2}.

![The month view](figures/plan-month.png "small")

The month view, reached with [[Month]] {1}, is a grid of days, Monday to Sunday. Each cell lists the three shifts with the names after them. A long name wraps onto a second line instead of being cut, and every nurse of a shift is listed. Days from the neighbouring months appear in grey.

The panel of a day lists the nurses of each shift. For a nurse it also carries the grey sentence "Only the physician or the head nurse can edit this schedule." {2} and has no button. If you try to change the rotation by another route, the server answers in French that only the doctor or the head nurse may edit the schedule.

> Note: The screen has no function to ask for a swap. Two nurses who want to exchange shifts agree with the head nurse, who changes the rotation.

## Planning the rotation (head nurse)

The head nurse builds the rotation day by day. The work is the same for every day: open the day, choose a nurse for a shift, add.

1. Select **Nurse Schedule** and move to the week you want to plan, with the arrows, with [[Today]] or with [[Month]].
2. Select the day. The panel "Schedule for" opens on the right, with three blocks: Morning, Afternoon and Night.
3. In the block of the shift, open the list [[Select a nurse]] {3} and choose the nurse.
4. Select [[Add a nurse]] {4}. The nurse appears in the block and in the calendar at once.

![A week of the rotation with a day open for editing](figures/plan-filled.png)

[[Add a nurse]] stays grey until a nurse is chosen. The lists contain the active nurse accounts, and a head nurse carries the mention "(Head nurse)" after the name, so you can also place yourself or a colleague head nurse. A nurse who is already in a shift no longer appears in the list of that shift, so a nurse cannot be added twice to the same shift. The lists also leave out the nurses whom the rules below forbid, and the panel carries a reminder that nurses on night duty the day before are not offered for the morning.

A shift can hold as many nurses as you add. Select [[Add a nurse]] again for each one. To take a nurse off a shift, select [[Remove]] on the line of the nurse. Nothing is asked before the removal and nothing is kept as a draft: the calendar is updated as soon as you select the button.

For an ordinary week, work through the days from Monday to Sunday. The week view {1} fills as you go, and you can check the result in the table without closing the panel. Select another day in the table to move the panel to it. To correct a day, select [[Remove]] {2} next to the wrong name, or choose another nurse in the list {3} and select [[Add a nurse]] {4}.

The application applies three rules to a nurse.

| Rule | What it means |
|---|---|
| Night is exclusive | A nurse on night duty cannot also work the morning or the afternoon of the same day. |
| Rest after a night | A nurse on night duty on a day cannot work the morning of the next day. The afternoon of the next day is allowed. The same rule applies the other way round: a nurse already on the morning of a day cannot be placed on the night before. |
| Morning and afternoon | The same nurse can work the morning and the afternoon of the same day. |

If a choice breaks a rule, the server refuses it and a red message under the panel says which one, for example "Mandatory rest: a nurse on night duty cannot work the morning shift the next day." This can happen at the edge of the displayed period, where the day before or after is not on screen, even though the list offered the nurse.

Nothing stops you from leaving a shift empty. An empty shift shows "No nurse assigned." in the panel.

> Caution: A removal cannot be undone. If you remove the wrong nurse, add the nurse again with the same steps.

## The patients who stay in the centre

The first nurse guide describes the screens of a hospitalised patient and the first entries. This chapter goes through the whole stay as a nurse lives it, in the order of the day.

A nurse has the same rights as a doctor on these screens. You can admit a patient, add a progress entry, discharge and download the discharge letter. No button is hidden from you, and every action carries your name.

### The list of the patients in the centre

![The list of the current stays](figures/hosp-list.png)

**Hospitalized Patients** {1}, under **Activity**, lists every open stay of the centre, whoever admitted the patient. The columns give the admission date and time, the length of the stay, the current status, the admission reason and the person who admitted the patient. A red triangle before a name means that the latest entry is Worsening {2}. Start your round with these lines. [[View record]] {3} opens the patient file on the same screen as the patient name.

The list shows open stays only. A patient who has been discharged leaves it at once. The status column shows "No update since admission." for a stay that has no entry yet.

### Admitting a patient

![The admission form](figures/admit-form.png)

1. Open the patient file from **Patients** or from the list, and select the **Hospitalization** tab. A patient without an open stay shows "This patient is not currently hospitalized."
2. Select [[Admit]] {1}. A grey form opens.
3. Type the reason {2}. The field is optional, but it is the only place where the reason is recorded. It then shows on the card, in the list and in the history, and it is printed on the discharge letter.
4. Select [[Confirm]] {3}.

The card then shows "Hospitalized since", the date and time with the length of the stay (for example "5 h 20 min"), your name next to "Admitted by" and the admission reason. The patient appears at once in the list of the patients in the centre.

### Recording the progress

Add an entry each time you take the measurements or change the treatment. An entry has a status and a note. The status is Improving, Stable or Worsening.

![The progress entry form](figures/status-form.png)

1. On the **Hospitalization** tab, select [[Update status]] {1}.
2. Choose the status {2}. The list opens on Improving, so check it every time.
3. Write the note {3}: the measurements, what you did, and what the next nurse must watch.
4. Select [[Confirm]] {4}.

![The card of a stay in progress](figures/status-card.png)

**Latest update** {1} shows the status of the most recent entry. The list **Current stay's clinical updates** {2} shows every entry, the newest first, with its status, the date and time, the name of the author and the note. The **History** part repeats the entries under the stay they belong to. [[Discharge]] {3} is on the same line as [[Update status]].

Entries cannot be edited or deleted. If one is wrong, add a new entry that corrects it. Write it as a handover: the nurse who comes after you will read these notes first.

### When the patient gets worse

A worsening is the status that must not wait. Save an entry with the status **Worsening**.

![An entry with the status Worsening](figures/aggravation-form.png)

1. On the **Hospitalization** tab, select [[Update status]].
2. Choose **Worsening** {1}.
3. Write what you found and what you did {2}. For example "Repeated vomiting since 14:00, pulse 118, very drowsy. Drip stopped, doctor called."
4. Select [[Confirm]] {3}.

The status turns red on the card, with a triangle, and the patient gets the same red triangle in the list of the patients in the centre. The mark stays until a later entry changes the status.

The application also warns the other doctors and nurses: each of them receives "Worsening reported: " followed by the patient name and your name on the bell, and selecting it opens the patient file. You do not receive your own alert.

> Note: The notification does not replace a call. Call the doctor on duty yourself, and use the note as the written record of the call.

### Discharging a patient

A nurse can close a stay. Do it when the doctor has decided on the discharge, and write the instructions the doctor gave.

![The discharge form](figures/discharge-form.png)

1. On the **Hospitalization** tab, select [[Discharge]] {1}. A form opens.
2. Choose the type in [[Discharge type]] {2}. It is required, and [[Confirm]] stays inactive until you choose. The types are Recovered, Transferred, Left against medical advice and Deceased.
3. Write the instructions in [[Discharge note]] {3}: the treatment to continue, the review date, the signs that must bring the patient back. The note is optional and is printed on the letter.
4. Select [[Confirm]] {4}.

The type cannot be changed afterwards, so check it, above all for Transferred and Deceased. The card then reads "This patient is not currently hospitalized." and the stay moves to the history. A closed stay accepts no more entries.

![The history after the discharge](figures/discharged.png)

The **History** shows the closed stay with its two dates, the admission reason, the type of discharge, the discharge note and the line "Discharge recorded by" followed by your name. The button [[Download discharge letter]] {1} is next to it. A returning patient is admitted again with [[Admit]] {2}. The second guide of the doctor describes the readmission.

### The discharge letter

The letter is a PDF of the stay in French: the centre header, the patient, the admission and discharge dates, the reason, a table of every entry, the type of discharge, "Prononcée par" followed by the name of the person who discharged, and the discharge note. A line for the signature of the referring doctor closes the letter. The length of the stay is written in hours and minutes for a short stay, and a short stay fits on one page.

![The first page of the letter](figures/letter.png "small")

Select [[Download discharge letter]] in the History. The letter can be downloaded again at any time and always shows the stay as it is now.

> Caution: A letter produced after a nurse's discharge still waits for the signature of a doctor. Print it, give it to the doctor to sign, then hand it to the patient.

## Working without a connection

The first nurse guide explains the yellow "Offline (your entries are saved)" indicator. Two screens of this guide do not keep a copy on the computer.

The Nurse Schedule reads the server. When the connection is lost, a yellow line says "Schedule unavailable offline: reconnect to view or edit it.", the cells show a question mark and the day panel reads "Unknown state" instead of "No nurse assigned." Editing is switched off. The rotation has not been erased. Wait for "Connected" and reopen the screen.

The hospitalisation screens also need the server. With a weak connection the tab of a patient who is in the centre can read "This patient is not currently hospitalized." and offer [[Admit]]. Do not admit, update or discharge until the indicator reads "Connected". Reopen the tab and check that the stay appears.

## Common mistakes

**Reading an unavailable calendar as an empty rotation.** A question mark in a cell means the schedule could not be loaded, not that nobody works. Wait for "Connected".

**Leaving the status on Improving.** The status list opens on Improving. Choose the real status each time, above all when the patient is worse.

**Relying on the bell after a Worsening entry.** It warns the team, but call the doctor when the patient needs someone now.

**Giving the letter to the patient unsigned.** The signature line of the referring doctor is on the second page.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Schedule unavailable offline: reconnect to view or edit it." | The schedule could not be loaded | Wait for "Connected" and reopen Nurse Schedule. |
| A red message such as "Mandatory rest: a nurse on night duty cannot work the morning shift the next day." | The choice breaks a shift rule | Choose another nurse or another shift (chapter 2). |
| The panel of a day says "Only the physician or the head nurse can edit this schedule." | Your account is not a head nurse | Ask the head nurse to make the change, or ask an administrator to give the right. |
| A red French message "Seuls le médecin ou le chef infirmier/infirmière peuvent modifier le planning." | The server refused the change for the same reason | Same as above. |
| "This patient is not currently hospitalized." for a patient who is in the centre, with "Offline" at the top | The stay could not be read | Wait for "Connected", reopen the tab, do not admit again. |
| "Erreur lors de l'admission du patient." | The admission did not reach the server | Check the connection and the list of the patients in the centre, then try once more. |
| "Erreur lors de la mise à jour du statut." | The entry was not saved | Check the connection and that the stay is open, then enter it again. |
| "Erreur lors de la sortie du patient." | The discharge was not saved | Check the connection. If the stay is in the History, it is closed. |

## Glossary {.unnumbered}

Head nurse
: A nurse account with the right to edit the rotation. The administrator gives the right in the user form.

Rotation
: The assignment of nurses to the three shifts of each day, shown in the Nurse Schedule.

Shift
: One of the three parts of a day: Morning, Afternoon, Night.

Stay
: The period between an admission and the matching discharge. A patient has at most one open stay.

Progress entry
: One line of a stay: a status, a note, the author and the time. It cannot be edited.

Worsening
: The status that marks the patient in red on the card and in the list of the patients in the centre.

Discharge letter
: The French PDF of a closed stay, with its entries, the type of discharge, the note and a signature line for the referring doctor.
