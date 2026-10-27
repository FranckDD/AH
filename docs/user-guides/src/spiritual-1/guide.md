---
title: Patients and spiritual notes
role: Spiritual counsellor
subtitle: Reading the toxicology follow-up, opening a patient file, finding discharged patients and writing your own spiritual notes.
version: 28 October 2026
output: spiritual-1-patients-sessions
---

## Before you start {.unnumbered}

This guide is for the spiritual counsellor of the centre. In Glostone-Care your account has two parts. The first is a reading account inside the toxicology follow-up: you see the patients who are followed for a substance, you open their files, and you read what the psychologist and the toxicology manager have written about them. The second is a notebook of your own, **Spiritual notes**, where you can record your meetings if you wish (chapter 5).

The screenshots come from a demonstration installation. The patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the spiritual counsellor can see and do

Your menu has three entries: **Toxicology Dashboard**, **Toxicology Monitoring** and **Spiritual notes**. Nothing else is open to your role. If you type the address of another screen, such as the patient register of the clinic, the user list or the appointments, the application shows an "Accès Interdit" page (access denied) with a button back to your dashboard.

You can read every active patient and every discharged patient of the toxicology service, not only the patients you meet. You can open the details and the file of each of them. You cannot record an evaluation, admit a patient, discharge one or readmit one. Your notes are not attached to any patient file. You cannot print a patient file. You see no invoice, no cash register, no laboratory result, no consultation and no appointment, and the application shows no notification bell to your role.

### Spiritual consultations and the notebook

A spiritual consultation is not invoiced. What is invoiced is the purchase of the notebook (carnet), and that sale is made by the secretary at the cash desk, with the patient registered at the secretariat. Neither step happens on your screens. If a patient tells you that the notebook was not sold or that a registration is wrong, send the patient back to the secretariat.

### Interface language

The application starts in French on a new computer. The language switch sits at the top right of every screen: select **EN** to work in English. The choice is kept on that computer.

> Note: Some texts stay in French in English mode: the clinical alerts on the dashboard ("Rechute critique", "Évaluation en retard"), the dates in the patient details window ("14 mars 1991"), the address "Non renseignée", the access denied page and the printed list. The substances are stored as typed, for example "Alcool" and "Cocaïne".

### Confidentiality

The file shows the clinical text of every evaluation, with the name of its author. You are among the few roles allowed to read it, so treat it as you treat a confession: do not repeat it outside the care team. The medical records and the prescriptions of the clinic are hidden from you, which is intended. Do not leave your session open on a shared computer, and select **Logout** at the end of the day.

## Signing in and the dashboard

Each member of staff has a personal account. Ask the administrator for yours.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again.

The application opens on the **Toxicology Dashboard**.

![The toxicology dashboard](figures/dashboard.png)

The dashboard {1} summarises the whole service. The four tiles {2} give the active patients, the relapse rate, the patients still in withdrawal (phase 1) and the admissions of the month. **Distribution by Phase** {3} counts the patients in each of the four phases, and **Distribution by Substance** sits beside it. **Psychologist Workload** {4} shows how many patients each psychologist follows. **Clinical Alerts** {5} lists the patients who need attention: a relapse has been recorded, or a patient has stayed in phase 1 for longer than the standard period of 15 days.

The alerts are a good way to choose whom to visit first. A patient who has just relapsed, or who has waited in phase 1 for months without a new evaluation, is often the one who most needs a conversation.

> Caution: In the demonstration, the tile **Admissions (Month)** read 0 on this dashboard while the same tile on the Toxicology Monitoring screen read 2. The monitoring screen is the one to trust for that figure. The other tiles agree on both screens.

## Reading the patient list

Select **Toxicology Monitoring** in the menu. This screen is your daily work table.

![The patient list](figures/list.png)

The title {1} gives the number of active patients followed. The tiles repeat the main figures. Each row shows the patient with the code and the substance, the current phase with a coloured bar, the number of relapses, and the referring psychologist. Two buttons end the row: **Details** {4} and **File** {5}. There is no Evaluate button for your role. The tabs {3} switch between **Active** and **Discharged** patients (chapter 4).

To find a patient, type a name or a patient code in the search box {2}. The list filters itself after a short pause. A search that matches nothing shows "No patient found." Clear the box to see everybody again.

> Note: The tiles follow the search. With "Ebogo" typed in the box, the list showed one patient and the tiles read 1 active patient and a relapse rate of 100%. These are the figures of the filtered list, not of the centre. Clear the search to read the real figures.

### The phases

A patient moves through four phases: Phase 1 Withdrawal, Phase 2 Detox, Phase 3 Reintegration and Phase 4 Aftercare. The phase changes only through the evaluation of the psychologist. The bar is red in phase 1, orange in phase 2 and blue in phase 3. Knowing the phase tells you what the patient is going through: in phase 1 the body is still recovering, and in phase 3 the question is the return to family and work.

## Details and the patient file

Select [[Details]] to see the identity of the patient, the contact and the address, the substance, the admission date, the referring psychologist and the current status.

![The details window](figures/details.png)

The window opens on **Identity** {1}. Scroll down for the **Legal guardian** {2}, the consent document and the notes written at admission. The legal guardian is the person to call in an emergency, and often the person who can tell you about the family. [[Open the full file]] {3} closes the window and opens the file.

You can also select [[File]] directly on a row. The file opens full screen, with the patient name, the code and the substance at the top.

Your file has a single tab, **Toxico History**. The **Medical Record** and **Prescriptions** tabs that other roles see are not shown to you. A **Progress** bar shows the patient on the four phases. Below it, the history lists each stay, with its start date, the psychologist and the substance. [[Close the file]], at the foot of the window, returns to the list.

### Reading the evaluations

Each evaluation appears in the history with its date, the decision (MAINTAIN, PROGRESS or REGRESS), the phases before and after, the name of the author, the observation and the recommendation.

![The evaluations of a stay](figures/file-evals.png)

The stay {1} groups everything that happened between the admission and the discharge. A regression carries a red **Relapse** label {2}. The recommendation {3} tells you what the psychologist asks of the team, for example a family meeting. Read it before you visit: it shows the state of mind of the patient this week and spares you from asking the same questions again.

The oldest line of a stay is the admission itself, written "Phase 1: Withdrawal, Admission initiale". A patient who comes back after a discharge starts a second stay, which appears under the first.

> Caution: In the demonstration, each evaluation appears twice in the history, the second copy showing the phase after the change as its starting phase (for example "PROGRESS phase 2 to phase 2"). Read the copies as one evaluation, and tell the administrator if you see this on a real patient.

## Discharged patients

The **Discharged** tab lists the patients whose follow-up has ended. This is where you find a patient who has left and comes back to see you, or whose family asks for news.

![The discharged patients tab](figures/discharged.png)

Filter the list by name or code {1}, by reason {2} (Recovery, Dropout, Exclusion, Other) and by a range of discharge dates. Each row shows the stays with their dates, the reason, the psychologist and the number of stays. [[View record]] {4} opens the file in reading mode, with the full history of the stays and a label "Discharged from programme". The discharge reason appears at the top of each stay.

[[Export PDF]] {3} is offered to you and requests a printable list with the filters you chose. The list is written in French whatever the language of the screen. In the test on the demonstration server the request itself was answered correctly (a PDF of about 20 KB), but the test browser had a download manager installed and could not save the file, so the saving of the document on the computer was not observed.

> Note: If a computer has a download manager installed in the browser, that program can intercept the PDF. Ask the administrator to exclude the application address from it.

There is no per-row PDF button on the discharged list for your role, because the printed file contains the clinical evaluations.

## Spiritual notes

The **Spiritual notes** entry {1} sits under the two toxicology entries. It opens your notebook. Writing a note is optional: nobody asks you to write one, the application sends no reminder and it counts nothing.

![The Spiritual notes entry in the menu](figures/notes-menu.png "small")

### Writing a note

The notes are not linked to a patient. One note records one meeting day, however many people you met. It takes less than a minute.

![The new note form](figures/notes-form.png)

1. Select [[New note]]. A form opens.
2. Check the **Meeting date** {1}. It shows today. Change it if you write the note later. The date cannot be in the future or more than one year in the past. This is the only required field.
3. Under **What was done** {2}, tick what applies: **Counsel**, **Prayer**, **Verse read**, **Discussion**, **Text given** and **Questions and answers**. Tick none, one or several.
4. If you ticked **Verse read**, type the verse in **Verse reference** {3}, for example "John 3:16".
5. If people did not wish to speak, tick **People did not want to talk** {4}. This is a normal outcome, not a failure.
6. Add free text in **Notes** {5} if you want to. The text is limited to 5000 characters.
7. Select [[Save]] {6}. The message "Note saved." confirms it.

A note with only a date is accepted.

### Reading, editing and deleting

The list shows the most recent meeting first. Each card gives the date, the name of the author and the ticks as small labels. The label **Last note** marks the most recent one.

![The list of notes](figures/notes-list.png)

[[New note]] {1} opens the form. The newest card carries **Last note** {2}. The ticks {3} appear as labels, and the verse reference appears beside **Verse read**. A meeting where nobody wished to talk shows its own label {6}. The buttons [[Edit]] {4} and [[Delete]] {5} appear only on the notes you wrote. [[Edit]] opens the same form. [[Delete]] asks "Delete the note of" followed by the date, and the deletion cannot be undone.

> Note: All the spiritual counsellor accounts read all the notes of the role, so a successor finds the history. Only the author can edit or delete a note.

### Who reads your notes

The promoter and the administrator can read all notes, with the name of the author, in read-only mode. They see the same list without any button to write. Nobody else can open the screen: the secretary, the doctor, the nurses, the psychologist and the toxicology manager do not see the entry, and the application refuses the address. The notes never appear in a patient file, in an export or in the statistics. Do not write anything in a note that you would not want the promoter or the administrator to read.

> Important: The notes are saved online only. If the connection to the server is lost, the form stays open with the message "No connection to the server. The note is not saved: your entries are kept, try again when the connection is back." Keep the window open and select [[Save]] again when the network is back. If you close the window, the entries are lost.

## Working without a connection

The toxicology screens and your notes read their data from the server. They have no copy on the computer.

![The list while the computer is offline](figures/offline.png)

Your screen shows a yellow badge {1} reading "Offline (your entries are saved)". This badge stays yellow for your role even when the connection is good, so it does not tell you the state of the network. What does tell you is the content of the screen. When the computer cannot reach the server, the list shows "0 patients followed" {2} and "No patient found." {3}, and the tiles fall to zero. That is not the real situation: the patients are simply not readable.

When you see an empty list, check the network cable or the Wi-Fi, reload the page and wait for the patients to come back. The toxicology screens save nothing from you, so you lose no data there, but you cannot read the files until the connection returns. A note cannot be saved without the network (see chapter 5).

## Your profile and password

The account icon at the top right, next to the language switch, opens **My Account**.

![The profile window](figures/account.png "small")

1. Select the account icon.
2. On the **Profile** tab {1}, correct the full name, the e-mail address or the phone number {3}.
3. Select [[Save]] {4}. The message "Profile updated successfully." confirms the change.

The user name and the role cannot be changed here. To change your password, open the **Password** tab {2}, type the current password, then the new one in the next two fields, and select [[Save]].

## Common mistakes

**Thinking that a note is compulsory.** It is not. Write one when it helps you.

**Looking for a note inside a patient file.** The notes are not linked to patients. They are in the **Spiritual notes** entry.

**Closing the form while the network is down.** The entries are lost. Wait for the connection and save first.

**Trusting the tiles after a search.** They follow the filtered list. Clear the search box first.

**Reading an empty list as "no patient".** After a network cut, reload the page before drawing any conclusion.

**Reading an evaluation twice.** A duplicated line in the history is a known fault of the demonstration, not a second interview.

**Expecting to evaluate, admit or discharge.** These buttons are not offered to you. Ask the psychologist or the toxicology manager.

**Telling a patient that the consultation is billed.** The consultation is free. Only the notebook is sold, at the secretariat.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Accès Interdit" page | Your role cannot open that screen | Select the button to your dashboard. |
| "0 patients followed" and "No patient found." | The server cannot be reached | Check the network, reload the page. |
| Tiles show 1 patient and 100% | A search is still typed in the box | Clear the search box. |
| The same evaluation twice in a history | A known duplicate of the demonstration version | Read it once. Tell the administrator. |
| The PDF of the list does not arrive | The browser did not save the document | Try again once. If a download manager is installed, exclude the application from it. |
| "No connection to the server" in the note form | The note is not saved yet | Keep the window open and select Save again when the network is back. |
| No Edit or Delete on a note | The note was written by another counsellor | Only the author can change it. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Evaluation
: The record of a psychologist interview: a decision (maintain, progress, regress), an observation and a recommendation.

Phase
: One of the four stages of the follow-up: Withdrawal, Detox, Reintegration, Aftercare.

Stay
: The period between an admission and a discharge. A patient who returns starts a new stay.

Relapse
: A regression recorded by the psychologist. It counts in the relapse rate.

Legal guardian
: The person to contact in an emergency for a patient, recorded at admission.

Note
: One record of a meeting day in **Spiritual notes**: date, optional ticks, optional text. Not linked to a patient.

Notebook (carnet)
: The booklet sold to the patient at the secretariat. It is the only invoiced item of a spiritual consultation.
