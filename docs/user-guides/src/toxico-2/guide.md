---
title: Discharge, readmission and exports
role: Toxicology manager
subtitle: Ending a stay in the toxicology programme, finding discharged patients, readmitting a patient who comes back, and printing the files and the lists.
version: 28 October 2026
output: toxico-2-discharge-readmission-exports
---

## Before you start {.unnumbered}

This guide is the second one for the toxicology manager. The first guide, "Toxicology manager 1: admission, phases and evaluations", covers signing in, the dashboard, the monitoring list, the admission of a patient, the evaluations written by the psychologist and the patient file. Read it first: this guide does not repeat those screens. It starts at the moment a stay ends.

You will find here the discharge of a patient, the **Discharged** tab and its filters, the readmission of a patient who left earlier, the way relapses are counted across stays, the PDF files you can print, what stays visible once a patient has left, and a few cases that need care. The screenshots come from a demonstration installation and the patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What you can do

Discharge, readmission and the exports are all done from one screen, **Toxicology Monitoring**. You can discharge any active patient, readmit any discharged patient, and print the toxicology file of any patient. You cannot change a phase and you cannot record an evaluation: those acts stay with the psychologist.

### Dates and language

The dates written in the tables and in the file windows read day, month, year ("26/10/2026"), like the dates of the PDF files. The date fields of the filters and of the forms follow the format of your computer. The patient details window is the one exception: it spells the month in French ("26 octobre 2026"). The PDF files are written in French whatever the language of the screen.

> Note: In the file window, the status words of the phases read "In progress", "Finished" and "Interrupted" in English mode. The comments that the application writes in the history ("Admission initiale", "Réadmission, séjour 2") stay in French.

## Discharging a patient

A discharge closes the current stay of a patient. It is the only way to end a stay: a patient who stops coming to the centre stays on the Active list, with the phase and the alerts of the dashboard, until you discharge him or her. Decide the reason together with the psychologist and, when the case is sensitive, with the promoter.

![The discharge window with the reason "Other"](figures/discharge-other.png "small")

1. In **Toxicology Monitoring**, on the **Active** tab, find the patient and select [[Discharge]] on the row. You can also open the file of the patient and select [[Discharge]] at the foot of the window.
2. Choose the reason {1}: **Recovery**, **Dropout**, **Exclusion** or **Other**.
3. Check the discharge date in [[Discharge date]]. It opens on today. You can choose an earlier day when the patient really left before you recorded it. The date cannot be in the future and cannot be before the admission of the current stay.
4. Write the note {2}. The note is optional for the first three reasons and required for **Other**. It takes up to 2000 characters. Write what a colleague will need in a year: what happened, who was informed, what follow-up is planned.
5. If the window warns about a hospital stay, tick the box (see "A patient who is in hospital" below).
6. Select [[Confirm discharge]] {4}.

If you choose **Other** and leave the note empty, the window stays open and shows the red message {3} "A note is required for the "Other" reason." Nothing is saved until you write the note or choose another reason. [[Cancel]] closes the window without any change.

When the discharge succeeds, a green message "Discharge recorded." appears for a few seconds. The patient leaves the **Active** list at once and the tiles move: in the demonstration the active patients went from 15 to 14 after the first discharge, then to 13 and 12 after two more.

The application records the date you chose and your name as the person who validated the discharge, and prints both later in the file. A wrong date is refused with "The discharge date cannot be in the future." or "The discharge date cannot be before the admission."

> Caution: A discharge cannot be undone from any screen. If you chose the wrong reason or discharged the wrong patient, the only way back is to readmit the patient (chapter 3), which starts a new stay and leaves the first one closed with the wrong reason. Check the name in the title of the window before you confirm.

## The Discharged tab

Select the **Discharged** tab {1}. It lists every patient whose last stay is closed, the most recent discharges first.

![The Discharged tab](figures/discharged-tab.png)

Each row gives the patient and the code, the dates of the last stay, the reason with a colour (green for Recovery, orange for Dropout, red for Exclusion, grey for Other), the psychologist of that stay, and the number of stays. Three buttons end the row: [[View record]], [[PDF]] and [[Readmit]]. The title above the tab, "patients followed", and the four tiles keep showing the active patients: they do not describe the list of this tab.

The four filters work together and apply as you type or choose:

- **Search** {2}: a part of a name or of a code.
- **Reason** {3}: one of the four reasons.
- **Discharged from** and **Discharged to** {4}: dates of discharge, limits included.

At the foot of the list, "Page 1 of 1 (2 patients)" gives the number of matching patients, with [[Previous]] and [[Next]]. A filter that matches nobody shows "No discharged patient matches these criteria." If the end date is before the start date, the list is emptied and the message "Fix the date range to show results." appears: correct a date, the list does not keep the previous period.

The same file is available for a patient who has been discharged: select [[View record]].

![The record of a discharged patient](figures/view-discharged.png "small")

The window shows the label "Discharged from programme" {1}, then a line such as "Discharged from the programme on 26/10/2026 (reason: Dropout)." with the name of the person who validated the discharge and the note, then the progress bar and the history, with the reason {2} and the note of the discharge at the head of each closed stay. It is read-only: there is no Discharge button, and the progress bar stays on the last phase reached. [[Export record (PDF)]] {3} prints the file (chapter 5).

## Readmitting a patient

A patient who left can come back. The application then opens a new stay in the same file: the identity, the code, the first stay and its evaluations are kept, and the new stay starts again in phase 1.

![The readmission form](figures/readmit-form.png "small")

1. Select the **Discharged** tab and find the patient.
2. Select [[Readmit]] on the row. The **Admission Form** opens with the patient already chosen. The yellow band {1} reads "Patient already followed: readmission, stay 2." and tells you that the phase restarts at 1 and the earliest date allowed, which is the date of the last discharge.
3. Check the admission date {2}. It opens on today. A date before the last discharge is refused by the field itself ("Value must be 26/10/2026.").
4. Check the referring psychologist {3}. The field opens on the psychologist who currently follows the patient, and it is required. Keep that name if the patient comes back to the same person. If you choose another psychologist, the application records a transfer with the reason "Readmission" in the file, so the change is never made without a trace.
5. Check the primary substance, then the guardian name {4} and the guardian contact. The substance of the last stay and the guardian recorded in the file are filled in for you. Ask whether they are still correct and change them if not. Both guardian fields are required.
6. Add a new signed consent if the patient signed one. Without a new file, the previous consent stays attached to the file.
7. Write the reason for the return in [[Admission Note]]. A new note replaces the previous admission note in the Details window, so copy anything you still need from the old one.
8. Select [[Validate Admission]] {5}.

The window closes, a green message "Readmission recorded, stay 2" appears and the patient is back in the **Active** list, in phase 1. The same patient also appears when you start from [[New Toxico Admission]] and search the name: the form shows the same yellow band, so both paths lead to the same readmission.

> Caution: The substance and the guardian are copied from the last stay, not asked again. A wrong value that you do not change is copied to the new stay and to the printed file.

### What is kept and what restarts

| Item | After a readmission |
|---|---|
| Patient code and identity | Unchanged |
| Earlier stays, evaluations, reasons and notes of discharge | Unchanged, grouped under their stay |
| Phase | Restarts at phase 1 |
| Psychologist, substance, guardian | Those entered on the form. A different psychologist is recorded as a transfer |
| Number of relapses | Kept, not reset |
| Admissions (month) tile | Increases: a readmission counts as an admission |

An admission is refused if the patient already has an active file: the form shows "This patient already has an active toxicology file: discharge them first." and Validate Admission stays pale.

## Transferring a patient to another psychologist

A patient keeps the same psychologist until you change it. The change is called a transfer. It is the only way to give a patient to another psychologist, and it leaves a written trace. Only the toxicology manager and the administrator have the button.

1. In **Toxicology Monitoring**, on the **Active** tab, select [[Transfer]] on the row of the patient. For a discharged patient, select [[View record]] and then [[Transfer]] at the foot of the file. The same button is at the foot of the file of an active patient.
2. The window **Transfer the patient** repeats the name and the current psychologist. Choose the new one in [[New responsible psychologist]]. The list offers the active accounts with the Psychologist role, without the current psychologist.
3. Write the reason in [[Reason for the transfer]]. It is required and holds up to 1000 characters. Write what the next psychologist needs to know: why the patient changes hands and what is in progress.
4. Select [[Confirm the transfer]].

The window closes and a green message "Patient transferred to" followed by the name appears. From that moment:

- The new psychologist is the referent of the patient. Only this person can write evaluations, and the button **Evaluate** moves to the rows of the new psychologist.
- If the patient has an open stay, the psychologist of that stay changes too. The stays already closed keep the psychologist they had.
- The new psychologist receives a notification. The former psychologist is not notified.
- Nothing is erased. The evaluations written before the transfer keep the name of their author, and the file shows a line "Psychologist change" with the date, the former and the new psychologist, who decided and the reason. The printed file shows the same lines.
- A psychologist whose account is limited to their own patients (see the administrator guide) no longer sees the patient in the lists. The patient moves to the tab **Previously followed patients** of that psychologist, in reading mode.

A transfer does not change the phase, the stay or the substance of the patient.

> Note: In the list of discharged patients, the column Psychologist still gives the psychologist of the last stay. After a transfer of a discharged patient it can show the former name, although the file already names the new referent. Open the file to check.

## Reading a patient over time

The file of a patient is the place to follow the progress. Open it with [[File]] for an active patient or [[View record]] for a discharged one.

![A file with two stays](figures/file-stays.png "small")

The file groups the history by stay, the oldest first. Each stay opens with a header: the number, the reason of the discharge or the label **Ongoing** {3}, the dates, the psychologist and the substance. Inside, the evaluations and the phases follow with the most recent first. The phase lines {1} show when each phase started, when it ended, and why. A phase left behind by an evaluation or closed by a discharge reads "Interrupted", and a phase that ended normally reads "Finished". The stay {2} that begins at a readmission carries its own first line "Réadmission, séjour 2".

### Counting relapses

A relapse is counted when the psychologist records an evaluation that sends the patient back one phase. The count belongs to the file of the patient, not to a stay.

- The count shows in the **Relapses** column of the Active list and feeds the relapse rate of the dashboard.
- A dropout, an exclusion or a readmission is not a relapse by itself. Only an evaluation creates one.
- A readmission keeps the count. In the demonstration, a patient with one relapse was discharged as a dropout and readmitted: the list showed "1 relapse" again, and the relapse rate went from 25% to 31% when he came back, because the rate is the share of active patients who have a relapse.

Read the relapses of the earlier stays before you judge a readmitted patient: a patient who comes back with two relapses in stay 1 is a different case from a first return.

## Printing and exporting

There are three PDF documents. Each opens from a button of the Discharged tab or of the file window. The only format is PDF: there is no Excel version of the toxicology lists.

![The export buttons](figures/exports-buttons.png)

### The list of discharged patients

Select [[Export PDF]] {1} above the table. The file contains the patients that match the filters on the screen, all pages, not only the page you see. It is titled "Toxicologie, Patients sortis" and gives the date and time of printing, the number of patients, and a line "Filtres" that repeats your filters (for example "Motif : Abandon"). The table gives the name, the code, the admission and the discharge of the last stay, the reason, the psychologist and the number of stays. A box "Visa de la direction" with a date line closes the document. The list is cut at 2000 patients, and the file says so if that happens.

![The printed list of discharged patients](figures/export-list.png "small")

Set the filters first. To print the dropouts of one month, choose the reason and the two dates, check the rows on the screen, then export.

### The file of one patient

Select [[PDF]] {2} on a row of the Discharged tab, or [[Export record (PDF)]] in the file window. Both produce the same document, in the French language of the printed forms.

![The first page of the printed file of a discharged patient](figures/export-dossier.png "small")

The file gives the identity, the status ("Sorti (dossier inactif)" or "Actif (en séjour)"), the guardian, then each stay with its substance, psychologist, reason of discharge, note, and "Sortie validée par" followed by your name. Under each stay come the table of phases and the table of evaluations. At the foot, two signature zones: the psychologist of the last stay, and the administrative manager. For a discharged patient, the name of the person who validated the discharge is already written under the second zone. For an active patient the second zone is blank. A patient with two stays, such as the readmitted patient of the demonstration, prints on two pages.

Do not sign a file before you have read it.

### The clinical file

The **Patients** entry of the menu opens the clinical file, with **Export PDF** and **Export Excel**. It is a different document from the toxicology file. Use it when a hospital or a doctor asks for the medical history of the patient.

## What happens to the file of a discharged patient

Nothing is deleted. The patient stays in the Discharged tab, the file stays readable, the evaluations stay attached to their stay, and the consent document stays available.

In the clinical file of the **Patients** menu, the patient keeps the label TOXICOLOGY next to the clinic label after the discharge.

![The Toxicology Follow-up tab of a discharged patient](figures/full-tox-discharged.png "small")

The **Toxicology Follow-up** tab {1} of that clinical file gives only the substance, the "Phase actuelle", the psychologist and the admission date. It does not say that the patient has been discharged, and it shows the phase reached before the discharge. Use the Discharged tab of the monitoring screen, not this tab, to know whether a patient is still in the programme.

## Cases that need care

### A patient who is in hospital

The clinic can hospitalise a patient who is also in the programme. The two stays stay separate, but the discharge window checks for you. When the patient has a hospital stay still open, a red block appears: "This patient has a hospital stay open since" followed by the date and time, "Toxicology discharge does not close it: the medical team will have to close it." You must tick "I understand, keep the hospital stay open" before [[Confirm discharge]] works. Without the tick the window answers "Confirm that the hospital stay stays open to continue." You cannot see the hospitalisations yourself: the menu of your role has no entry for them. Tell the doctor or the nurse that the patient left the programme, so that the hospital stay is handled, and write it in the note.

![The discharge window of a patient with a hospital stay still open](figures/discharge-hospital.png "small")

The red block carries the box {1}. [[Confirm discharge]] {2} works only once the box is ticked.

### A patient who relapses after a discharge

A patient discharged as **Recovery** who comes back after a relapse is readmitted like any other. Choose the reason of the return in the admission note, keep the earlier stay as it is, and tell the psychologist that the count of relapses continues from the previous stay.

### A patient who left without notice

Discharge him or her as **Dropout** on the day you decide, and write in the note the date of the last visit. If the family brings the patient back the same day, readmit at once: the stays then both carry today's date, which is correct.

### Two people with the same name

The search of the readmission form and the filters of the Discharged tab match a part of a name. Always check the code and the date of birth before you select **Readmit** or [[Confirm discharge]].

## Working without a connection

The toxicology lists read from the server and keep no copy on the computer.

![The Discharged tab while the computer is offline](figures/offline-discharged.png "small")

The yellow badge {1} reads "Offline" when the computer cannot reach the server, and goes back to "Connected" by itself within 15 seconds of the return of the link. The Active list then shows "Cannot load the data while offline. Figures shown would not be reliable." with a [[Retry]] button, and the tiles read a dash. The Discharged tab {2} shows the red message "Unable to load discharged patients." with a [[Retry]] button. With no Active list there is no row to discharge, and with no discharged list there is nothing to readmit. Keep the decision on paper, select Retry when the connection is back, and record the discharge then. Do not treat a failed load as "no patient".

## Your profile and password

The account icon at the top right opens **My Account**, where you correct your name, e-mail address and phone number and change your password. The steps are in the first guide, chapter "Your profile and password".

## Common mistakes

**Discharging the wrong patient.** Read the name in the title of the window. Undoing it means a readmission and a wrong reason left in the history.

**Leaving the note empty.** The note is optional except for "Other", but it is the only explanation the next reader will have.

**Trusting the title of the Discharged tab.** The count at the top and the tiles are those of the active patients.

**Accepting the readmission form without reading it.** The substance and the guardian are copied from the last stay. Check them with the patient.

**Transferring without a reason.** The reason is required, and it is the only explanation the next psychologist will read. The window shows "The reason is required." and saves nothing until it is written.

**Choosing the psychologist who already follows the patient.** The current psychologist is not offered in the list. If the server answers "This psychologist already follows the patient.", the file was changed in the meantime: reload and check.

**Ignoring the hospital warning.** The toxicology discharge does not close a hospital stay. Tell the medical team.

**Reading the Toxicology Follow-up tab of the clinical file as the status of the patient.** It does not show the discharge.

**Exporting before setting the filters.** The list file follows the filters you see.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| Confirm discharge does nothing and a red message appears | "Other" chosen without a note, or no reason chosen | Write the note or choose a reason. |
| "This patient already has an active toxicology file" | The patient is already back in the Active list | Open the file. Do not readmit again. |
| "Value must be" on the admission date | The date is before the last discharge | Use the date of the discharge or a later one. |
| Validate Admission stays pale on a readmission | The psychologist or a guardian field is empty | Fill the fields marked with a star. |
| "The discharge date cannot be in the future." or "...before the admission." | The date chosen is outside the stay | Choose a date between the admission and today. |
| "Confirm that the hospital stay stays open to continue." | The patient has an open hospital stay and the box is not ticked | Read the warning, tick the box, then confirm. |
| "The reason is required." in the transfer window | The reason is empty | Write the reason, 1000 characters at most. |
| "Choose the new psychologist." | No psychologist selected | Choose one in the list. |
| "The chosen psychologist was not found, is inactive or does not have the psychologist role." | The account changed after you opened the window | Close the window, open it again and choose another account. |
| "Fix the date range to show results." | The end date is before the start date | Correct one of the dates. |
| "No discharged patient matches these criteria." | The filters leave nobody | Clear a filter. |
| "Unable to load discharged patients." | The server cannot be reached | Check the network, then select Retry. |
| "PDF export failed. Please try again later." | The PDF could not be produced | Try again once. If it persists, tell the administrator. |
| A discharged patient still shows a phase in the clinical file | The Toxicology Follow-up tab does not show the discharge | Check the Discharged tab. |

## Glossary {.unnumbered}

Discharge
: The closing of the current stay, with a reason, a date and a note. The date is today unless you choose an earlier day.

Discharge reason
: Recovery, Dropout, Exclusion or Other. A note is required for Other.

Readmission
: The return of a discharged patient: a new stay in the same file, starting in phase 1.

Relapse
: A regression recorded by an evaluation. The count follows the patient across stays.

Stay
: The period between an admission and a discharge. Stay 2 is the first readmission.

Transfer
: The change of the referent psychologist of a patient, decided by the toxicology manager or the administrator, with a written reason.

Visa de la direction
: The line at the foot of the printed list, where the person in charge of the centre signs.
