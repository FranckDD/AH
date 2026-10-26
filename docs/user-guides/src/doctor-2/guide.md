---
title: Hospitalisation and follow-up
role: Doctor
subtitle: Admitting a patient, recording the progress of the stay, raising an aggravation, discharging with the discharge letter, readmitting, and following a patient over time.
version: 26 October 2026
output: doctor-2-hospitalisation-follow-up
---

## Before you start {.unnumbered}

This is the second guide for the doctor. The first one covers consultations, prescriptions, laboratory results, appointments, the offline mode and your profile, and it explains how to sign in. Nothing from it is repeated here. This guide covers the patients who stay in the centre: the Hospitalized Patients screen, the Hospitalization tab of a patient file, and the other places where you follow a patient from one visit to the next.

The screenshots come from a demonstration installation, and the patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### Who does what

Doctors and nurses see the same hospitalization screens and can do the same four things: admit a patient, add a progress entry, discharge, and download the discharge letter. Every entry carries the name of the person who saved it, so write it as you would sign it. The reception desk, the laboratory and the other services do not see these screens.

You can admit any patient who has a file, including a patient who is followed in toxicology or spiritual care. The admission itself places the patient in the clinical follow-up.

### Language

Interface labels in this module are in English when you select **EN** at the top right, as described in the first guide. Three things stay in French: the discharge letter, the error messages shown in red under the Hospitalization card, and the file exports. The letter and the exports are documents for the patient file, and their headings do not follow the interface language.

## Where hospitalization lives

Three places show the stays, and each answers a different question.

![The list of current stays](figures/hosp-list.png)

**Hospitalized Patients** {1} in the menu lists every patient who is in the centre now, whoever admitted them. The columns give the admission date and time, the number of days, the current status {2}, and the person who admitted the patient. A small red triangle before a name means the latest entry is a worsening: look at those lines first. The patient name and [[View record]] {3} both open the patient file.

The list shows open stays only. A patient who has been discharged leaves the list at once and stays visible in the history of the file (chapter 6).

The **Hospitalization** tab of a patient file is where you work. Everything in chapters 2 to 6 happens there. Open the file from **Patients**, from the list above, or from a notification, then select the tab. The tab sits next to **Medical Record**, **Exams** and **Treatments**.

The **Dashboard** counts the stays in a tile.

![The Dashboard with the Current stays count](figures/dashboard.png)

The block **Current stays** {1} in Quick access and the tile **Current stays (establishment)** show the number of open stays in the whole centre, not only yours. A click on the block opens the list. The Dashboard keeps its figures for about five minutes, so after an admission or a discharge the count can lag behind the list. The list is always current.

> Note: Trust the list, not the Dashboard count, when you need the exact number of patients in the centre at this moment.

## Admitting a patient

An admission opens a stay. It records who admitted the patient, when, and why. A patient can have only one open stay at a time.

![The admission form on the Hospitalization tab](figures/admit-form.png)

1. Open the patient file and select the **Hospitalization** tab. A patient without an open stay shows "This patient is not currently hospitalized."
2. Select [[Admit]] {1}. A grey form opens under the title.
3. Type the reason in [[Admission reason]] {2}. The field is optional, but write it: it is the only place where the reason is recorded, and it is printed on the discharge letter.
4. Select [[Confirm]] {3}.

The card now shows "Hospitalized since", the date and time, the number of days and your name under "Admitted by". The patient appears in the Hospitalized Patients list at once.

[[Cancel]] closes the form without saving anything.

If the patient already has an open stay, the server answers "Ce patient est déjà hospitalisé (séjour en cours)." in French. The [[Admit]] button is hidden for an inpatient, so this happens only when two people admit the same patient at nearly the same time. Nothing is duplicated.

> Caution: The admission reason is not shown again on the screen after you confirm. Check the text before you select [[Confirm]]. You will find it again only on the discharge letter.

## Recording progress during the stay

Each time you see the patient, add a progress entry. An entry has a status and a note. The status is one of three values.

| Status | When to use it |
|---|---|
| Improving | The patient is better than at the previous entry. The label is green. |
| Stable | No significant change. The label is grey. |
| Worsening | The patient is worse. The label is red and the alert in chapter 4 applies. |

![Adding a progress entry](figures/status-form.png)

1. On the **Hospitalization** tab, select [[Update status]] {1}. A form opens.
2. Choose the status in the list {2}. The list opens on "Improving".
3. Write the note {3}: the measurements, what you did and what you expect. The note is optional.
4. Select [[Confirm]] {4}.

The entry is added at once and the card shows the new status next to **Latest update**.

![The progress of the current stay](figures/status-list.png)

**Latest update** {1} shows the status of the most recent entry. The list **Current stay's clinical updates** {2} shows every entry of the stay, the newest first, with its status, its date and time, the name of the author and the note. The same entries are repeated in the **History** {3} part, under the stay they belong to.

Entries cannot be changed or deleted. If an entry is wrong, add a new one that corrects it. The new entry becomes the latest one.

> Note: The status of the entry is a clinical judgement, not a count. Two doctors can follow the same patient, and each entry shows who made it. Read the previous notes before you add yours.

## The aggravation alert

A worsening is the one status that must not wait until someone opens the file. When you save an entry with the status **Worsening**, the patient is marked in two places on screen.

![An entry with the status Worsening](figures/aggravation-form.png)

1. On the **Hospitalization** tab, select [[Update status]].
2. Choose **Worsening** {1}.
3. Write in the note {2} what you found and what is needed, for example "Fever 39.8 and repeated vomiting. Drowsy. Blood sugar to check."
4. Select [[Confirm]] {3}.

On the card, the status turns red, and the patient gets a red triangle in the Hospitalized Patients list (see the first figure of chapter 1). The mark stays until the next entry changes the status.

> Caution: The application is meant to send a notification to every other doctor and nurse when you save a Worsening entry, but in the demonstration installation no notification arrived on the bell of the nurse accounts. Do not rely on the bell to warn the team. Tell the nurse on duty yourself, and keep the entry as the written record.

## Discharging a patient and the discharge letter

A discharge closes the stay. It asks for the reason of the departure and prints nothing by itself: the letter is a separate download.

![The discharge form](figures/discharge-form.png)

1. On the **Hospitalization** tab, select [[Discharge]] {1}. A form opens.
2. Choose the type of discharge in [[Discharge type]] {2}. The field is required, and [[Confirm]] stays inactive until you choose.
3. Write the instructions in [[Discharge note]] {3}: the treatment to continue, the review date and the signs that must bring the patient back. The note is optional, and it is printed on the letter.
4. Select [[Confirm]] {4}.

There are four types.

| Type | Meaning |
|---|---|
| Recovered | The patient leaves in good health. |
| Transferred | The patient goes to another facility. |
| Left against medical advice | The patient leaves although you advised against it. |
| Deceased | The patient died during the stay. |

After the confirmation, the card shows "This patient is not currently hospitalized." and the stay moves to the history. The patient leaves the Hospitalized Patients list. A stay that is closed cannot receive more progress entries.

### The discharge letter

![The discharge letter](figures/letter.png "small")

The letter is a PDF of the stay: the centre header, the patient, the admission date and the person who admitted the patient, the discharge date, the length of the stay, the reason of admission, a table of every progress entry, then the type of discharge, the name of the doctor who pronounced it and the discharge note. A second page carries a signature line for the referring doctor. The letter is written in French.

1. Open the file of the discharged patient and select the **Hospitalization** tab.
2. In **History**, find the stay.
3. Select [[Download discharge letter]]. The browser saves a file named like lettre_sortie_1293.pdf.

The button exists only for a stay that has been discharged, and it can be used again at any time, for example when the patient asks for a second copy. The letter always shows the data as it is now.

> Note: Print the letter, read it, and sign the second page before it goes to the patient. The signature line is on paper only.

## Readmission and the history of a patient

A discharged patient who comes back is admitted again with the same button. Nothing links the new stay to the old one except the file they share.

![The history of two stays](figures/history.png)

1. Open the file and select the **Hospitalization** tab. After a discharge the card shows [[Admit]] again.
2. Select [[Admit]], write the new reason, and select [[Confirm]]. Write what is new, for example "Return of fever and cough five days after discharge."

The card now shows the new stay at the top, with its own date, its own status and its own entries. The **History** {1} lists every stay of the patient, the newest first. An open stay shows its start date and no end date. A closed stay shows its two dates, the type of discharge, the name of the doctor who recorded the discharge, its progress entries and the button [[Download discharge letter]] {2}.

The history is the answer to "has this patient been admitted before, and how did it end?" Read it before you admit a patient again: the earlier notes often explain the second stay.

## Following a patient over time

A stay is one event. The follow-up of a patient also runs through the consultations before and after it, and you have two ways to read them.

![The consultation history in the patient file](figures/followup-tab.png)

The tab **Medical Record** {1} of the file lists the consultations of the patient, the newest first. Each one shows the diagnosis, the date, the author, the vitals, the notes, the allergies and the written treatment. [[New consultation]] {2} starts a new visit, and [[Modifier]] {3} edits the latest one. An older consultation shows the label "Consultation closed: a more recent consultation exists" and can no longer be changed. The first guide explains that rule.

The cards at the top of the file show the last blood pressure, weight and temperature, and the known allergies, taken from the latest consultation. After a stay, write a consultation that records the vitals at discharge, so that the cards are current.

![The Consultations screen filtered on one patient](figures/consultations-patient.png)

The **Consultations** screen of the menu lists every consultation of the centre. Type the name or the code of the patient in the search box {1} to keep that patient only. The count above the table says how many consultations were found. The filters on the right narrow the list by reason, severity and dates. Use it to compare the successive diagnoses of a patient on one screen, or to find a patient's visits between two dates.

> Note: The progress entries of a stay do not appear in the consultation list. They live only in the Hospitalization tab and on the discharge letter.

## Exporting the file

The header of every patient file has two buttons, [[Export PDF]] and [[Export Excel]]. They save the whole file of the patient: a PDF named dossier_ followed by the patient number, or an Excel workbook of the same name.

The PDF has the centre header, the patient identity, then the medical history (date, reason, diagnosis), the prescriptions, the laboratory results, and, for a patient followed by another service, the toxicology and spiritual sections. The Excel workbook holds one sheet per section: Patient, Historique medical, Prescriptions and Labo. The section titles are in French, like the rest of the export. A signature line for the referring doctor closes the PDF.

> Caution: The export does not contain the hospitalization stays, their progress entries or the discharge notes. For the record of a stay, download the discharge letter (chapter 5). Do not hand the file export to a patient as proof of a hospitalization.

The patient list also has an export of the list itself, which is a list of patients and not a medical file. It is not used for follow-up.

## Working without a connection

The hospitalization screens read and write on the server directly. They do not keep a copy on the computer, as the consultations do.

![The Hospitalization tab while the connection is down](figures/offline-tab.png "small")

When the indicator {1} reads "Offline (your entries are saved)", the tab of an inpatient shows "This patient is not currently hospitalized." {2} and offers [[Admit]] {3}. This is wrong: the screen could not read the stay, so it shows an empty one. The patient is still hospitalized.

Do not admit, update or discharge while the indicator reads "Offline". An admission made in this state is not kept: the form stays open and the card answers in French with the red line "Erreur lors de l'admission du patient." Wait for "Connected", reopen the tab, check that the stay appears, and then make your entry. The Hospitalized Patients list and the Dashboard count need the connection in the same way.

## Common mistakes

**Reading an empty Hospitalization tab as a discharged patient.** With a weak or lost connection the tab can look empty for an inpatient. Check the indicator at the top right, then the Hospitalized Patients list.

**Putting the admission reason in the first progress entry only.** The reason field of the admission is the one the letter prints. A short reason there saves a long note later.

**Entering Worsening and counting on the bell.** The alert on the screen is reliable. The notification to the team has not been seen to arrive. Call the nurse.

**Choosing the discharge type in a hurry.** The type cannot be changed after the confirmation, and it is printed on the letter. Check it, above all for Transferred and Deceased.

**Looking for the stays in the file export.** They are not there. Use the discharge letter.

**Admitting a second time instead of reading the history.** A patient who is already inpatient has no [[Admit]] button. If you cannot find the button, the stay is open: look for the patient in the list.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "This patient is not currently hospitalized." for an inpatient, with "Offline" at the top | The stay could not be read without the server | Wait for "Connected" and reopen the tab. Do not admit again. |
| "Erreur lors de l'admission du patient." | The admission was refused or the server was unreachable | Check the connection and the Hospitalized Patients list, then try again once. |
| "Ce patient est déjà hospitalisé (séjour en cours)." | An open stay exists for this patient | Open the stay from the Hospitalized Patients list. |
| "Erreur lors de la mise à jour du statut." | The entry was not saved | Check the connection and that the stay is still open, then enter it again. |
| "Erreur lors de la sortie du patient." | The discharge was not saved | Check the connection. Look at the History: if the stay is closed, nothing is left to do. |
| The Download discharge letter button has no effect | The letter could not be created or reached | Check the connection and try again. If it repeats, tell the administrator. |
| The Dashboard count differs from the list | The Dashboard keeps its figures for about five minutes | Use the list. |
| No bell notification after a Worsening entry | The notification is not delivered at present | Tell the team yourself. |

## Glossary {.unnumbered}

Admission
: The opening of a stay, with its reason, its date and the name of the person who admitted the patient.

Discharge
: The closing of a stay, with a type and an optional note. The type is final.

Discharge letter
: The French PDF of a closed stay, with the progress entries, the type of discharge and the discharge note.

Progress entry
: One line of the stay: a status (Improving, Stable or Worsening), a note, the author and the time.

Stay
: The period between an admission and the matching discharge. A patient has at most one open stay.

Worsening
: The status that marks the patient in red on the card and in the Hospitalized Patients list.
