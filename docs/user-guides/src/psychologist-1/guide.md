---
title: Patients and sessions
role: Psychologist
subtitle: Reading the toxicology follow-up, opening a patient file, recording the evaluation that moves a patient between phases, finding discharged patients and printing the file.
version: 28 October 2026
output: psychologist-1-patients-sessions
---

## Before you start {.unnumbered}

This guide is for the psychologist of the centre. In Glostone-Care the psychologist works inside the toxicology follow-up: you read the patients who are followed for a substance, you open their files, and you record, after each interview, an evaluation that keeps the patient in the same phase, moves the patient forward, or sends the patient back. That evaluation is the one act that only the psychologist can perform, and only for the patients you are the referent of.

The screenshots come from a demonstration installation. The patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the psychologist can see and do

Your menu has two entries: **Toxicology Dashboard** and **Toxicology Monitoring**. Nothing else is open to your role. If you type the address of another screen, such as the patient list of the clinic or the user list, the application shows an "Access denied" page with a link, [[Go to my dashboard]], back to your dashboard.

You are the **referent** of a patient when you are the psychologist currently named in the file. You can record an evaluation only on your own patients. Whether you can read the other patients depends on your account. By default you read every patient followed in toxicology and open their files, including their last medical records and prescriptions. If the administrator ticked the box "Sees only their own toxicology patients" on your account, you see only the patients you are the referent of, and your dashboard figures count only those patients (see "A limited account" below). You cannot admit a patient, discharge a patient or readmit one: those actions belong to the toxicology manager and the administrator. You do not see invoices, the cash register, laboratory results or appointments, and the application shows you a notification bell only for transfers: when the toxicology manager or the administrator names you as the new referent of a patient, you receive a notification there, and clicking it opens the patient file.

### Interface language

The application starts in French on a new computer. The language switch sits at the top right of every screen: select **EN** to work in English. The choice is kept on that computer.

> Note: Some texts stay in French in English mode. The clinical alerts on the dashboard ("Rechute critique", "Évaluation en retard"), the dates in the patient details window ("14 mars 1991"), the comments that the application writes in the history ("Admission initiale", "Réadmission, séjour 2") and the printed PDF are in French. The substances are stored as typed, for example "Alcool" and "Cocaïne". The dates in the lists and in the file read day, month, year ("26/10/2026").

### Confidentiality

The text you write in an evaluation is clinical. The toxicology manager, the spiritual counsellor, the assistant and the administrator can read it. The promoter, who validates discharges, sees the decision and the dates but not your observations. A patient file also shows the last three medical records and the last three prescriptions of the clinic for the patients you currently follow, so a patient who is treated for a physical illness is visible to you in full. Do not leave your session open on a shared computer, and use **Logout** at the end of the day.

## Signing in and the dashboard

Each member of staff has a personal account. Every evaluation carries the name of the person who saved it.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again.

The application opens on the **Toxicology Dashboard**.

![The toxicology dashboard](figures/dashboard.png "small")

The dashboard {1} summarises the whole toxicology service. The four tiles {2} give the active patients, the relapse rate, the patients still in withdrawal (phase 1) and the admissions of the month. **Distribution by Phase** {3} counts the patients in each of the four phases, and **Distribution by Substance** sits beside it. **Psychologist Workload** {4} shows how many patients each psychologist follows. **Clinical Alerts** {5} lists the patients who need attention: a relapse has been recorded, or a patient has stayed in phase 1 for longer than the standard period (15 days).

The tiles count the whole service. They do not change when you type in the search box of the monitoring list, and the **Admissions (Month)** tile reads the same here and on the Toxicology Monitoring screen. When the server cannot be reached, the dashboard shows "Cannot load the data" with a [[Retry]] button and the tiles read a dash instead of 0.

## Reading the patient list

Select **Toxicology Monitoring** in the menu. This screen is your daily work table.

![The patient list](figures/list.png)

The title {1} gives the number of active patients followed. The tiles repeat the main figures. Each row shows the patient with the code and the substance, the current phase with a coloured bar, the number of relapses, and the referring psychologist. The buttons at the end of the row open the **Details** {4}, the **File** {5} and the **Evaluate** {6} window. **Evaluate** is shown only on the rows of the patients you are the referent of. The tabs {3} switch between **Active** and **Discharged** patients (chapter 6).

To find a patient, type a name or a patient code in the search box {2}. The list filters itself after a short pause. A search that matches nothing shows an empty table. Clear the box to see everybody again.

### The phases

A patient moves through four phases: Phase 1 Withdrawal, Phase 2 Detox, Phase 3 Reintegration and Phase 4 Aftercare. The phase changes only through your evaluation. The bar is red in phase 1, orange in phase 2 and blue in phase 3.

### Details

Select [[Details]] to see the identity of the patient, the contact and the address, the substance, the admission date, the referring psychologist, the legal guardian (name and phone number), the consent document and the notes written at admission.

The legal guardian is the person to call in an emergency. When a consent was uploaded, [[Download the document]] opens it in a new browser tab. The document is protected: it opens only while you are signed in, and each reading is recorded in the audit log. If it cannot be opened, the window says "Could not open the file. Try again or contact the administrator." [[Open the full file]], at the foot of the window, closes it and opens the file described in the next chapter.

## The patient file

Select [[File]] on a row. The file opens full screen, with the patient name and code at the top and three tabs.

![The history tab of a file](figures/file-history.png)

**Toxico History** {1} shows the progress bar and then each stay of the patient with its phases and its evaluations, the most recent first. **Medical Record** {2} lists the last three consultations of the clinic for this patient. **Prescriptions** {3} lists the last three prescriptions. [[Export record (PDF)]] {4} prints the file (chapter 7). [[Close the file]] {5} returns to the list.

The medical tabs give you only the last three entries. The button that opens the complete history on the clinic side is not offered to your role. When a patient has no entry, the tab says so ("No prescription.").

Read this tab before an interview: a fever, a recent injury or a treatment that causes drowsiness changes how the patient presents.

### The history of evaluations

Each evaluation appears in the history with its date, the decision, the phases before and after, your name, your observation and your recommendation. A regression carries a red **Relapse** label.

The stay groups everything that happened between the admission and the discharge. A patient who comes back after a discharge starts a second stay, which appears under the first.

### A limited account

When the administrator has limited your account to your own patients, the screens change in four ways.

- The lists of **Active** and **Discharged** patients, the search and the dashboard figures cover only the patients you currently follow. The split by psychologist on the dashboard is hidden.
- A third tab, **Previously followed patients**, lists the patients that the toxicology manager transferred to a colleague. Each row gives the patient, the current psychologist and the status.
- A file opened from that tab is in reading mode. A blue band says "Read-only view: you followed this patient, but they are no longer under your care." You can read the history of stays, the evaluations you wrote and the transfers. You cannot evaluate, export the file or open the consent document, and the **Medical Record** and **Prescriptions** tabs are not offered.
- A patient who has never been in your care is not found at all, even by typing the exact name.

When a patient is transferred to you, the patient appears in your lists and you become the only psychologist who can evaluate. The file shows the line "Psychologist change" with the reason written by the toxicology manager: read it before the first interview. The evaluations written earlier keep the name of their author.

## Recording an evaluation

The evaluation is the written result of an interview. It records one decision about the phase, your clinical observation and, if you wish, your recommendation. Do it after the interview, while your notes are fresh.

1. In **Toxicology Monitoring**, find one of your patients.
2. Select [[Evaluate]] on the row. The window **Clinical & Behavioral Evaluation** opens and repeats the patient name and the current phase.

![The evaluation window](figures/eval-form.png)

3. Choose the decision {1} {2}: **Maintain Phase** keeps the patient where he or she is, **Progression** moves the patient to the next phase, **Regression / Relapse** sends the patient back one phase. Each choice states the target phase underneath. Maintain is selected when the window opens.
4. Write your finding in **Clinical Observations** {4}. The field is required and holds up to 500 characters. A counter under the field shows what remains.
5. Write the follow-up you ask for in **Recommendations / Prescriptions** {5}. This field is optional and holds up to 200 characters.
6. Read the blue **Summary** line, which says in words what will happen, for example "The patient will move from phase 1 to phase 2".
7. Select [[Submit Evaluation]] {6}.

The button stays pale and does not work while the observation is empty. After a successful submission the window closes by itself and the list refreshes with the new phase. The application shows no confirmation message, so check the row or the file history. Each submission produces one line in the history.

When you choose Progression, the card and the button turn green and the summary confirms the move. Write the observation so that a colleague who did not attend the interview understands why the patient advances.

### Relapse and regression

A regression is recorded as a relapse and counts in the relapse rate of the dashboard.

![A regression with its warning](figures/eval-regress.png)

When you choose **Regression / Relapse** {1}, a red warning {2} reminds you that a relapse will be recorded and that a detailed justification is required. The observation must then have at least 10 characters, otherwise the application asks for more detail and the button stays inactive. The summary {3} says "The patient will go back from phase 2 to phase 1 (relapse)".

> Caution: A regression of a patient who is already in phase 1 keeps the patient in phase 1 but still records a relapse. Choose Maintain Phase if there was no relapse.

An evaluation cannot be edited or deleted from your screens. If you chose the wrong decision, record a new evaluation that explains the correction, and tell the toxicology manager.

At phase 4 the Progression choice keeps the patient in phase 4.

## Discharged patients

The **Discharged** tab lists the patients whose follow-up has ended. You can read them and print them, but you cannot discharge anyone or readmit a patient.

![The discharged patients tab](figures/discharged.png)

Filter the list by name or code {1}, by reason {2} (Recovery, Dropout, Exclusion, Other) and by a range of discharge dates. [[View record]] {4} opens the file in reading mode, with the full history of the stays. [[PDF]] {5} prints the file of that patient. [[Export PDF]] {3} prints the list with the filters you chose.

## Printing the file and the list

Three buttons produce a PDF: **Export record (PDF)** in a patient file, **PDF** on a row of the discharged list, and **Export PDF** above that list. Your browser saves the document in its download folder.

![The first page of the exported file](figures/export-pdf.png "small")

The printed file carries the header of the centre, the identity of the patient, the guardian, each stay with its phases, and the table of evaluations with their date, decision, phases, observation, recommendation and author. At the foot are two signature zones: one for the psychologist, with your name, and one for the administrative manager. The document is written in French whatever the language of the screen.

A printed file contains the clinical text of your evaluations. Keep it in the patient folder and do not leave copies on shared printers.

## Working without a connection

The toxicology screens read their data from the server. They have no copy on the computer.

![The list while the computer is offline](figures/offline.png)

When the computer cannot reach the server, the badge {1} turns yellow and reads "Offline". The application checks the server every 15 seconds, so the badge goes back to "Connected" by itself when the link returns. The list then shows the message "Cannot load the data while offline. Figures shown would not be reliable." {2} with a [[Retry]] button {3} in place of the table, and the tiles read a dash. That is not the real situation: the patients are simply not readable.

When you see this message, check the network cable or the Wi-Fi, then select [[Retry]]. You cannot open the evaluation window without the list, so keep your interview notes on paper and enter the evaluation as soon as the patients are back.

## Your profile and password

The account icon at the top right, next to the language switch, opens **My Account**.

![The profile window](figures/account.png "small")

1. Select the account icon.
2. On the **Profile** tab {1}, correct the full name, the e-mail address or the phone number {3}.
3. Select [[Save]] {4}. The message "Profile updated successfully." confirms the change.

The user name and the role cannot be changed here. To change your password, open the **Password** tab {2}, type the current password, then the new one twice, and select [[Save]]. Choose a password of at least 8 characters.

## Common mistakes

**Submitting twice.** Select Submit Evaluation once and wait. The window closes by itself.

**Choosing Regression for a patient who did not relapse.** The relapse is counted in the statistics of the whole service.

**Reading a failed load as an empty service.** After a network cut, the list shows an error message and a dash in the tiles. Select Retry before you draw any conclusion.

**Looking for Evaluate on a colleague's patient.** The button is shown only on the rows of the patients you are the referent of. If a patient was transferred to you or from you, the button moves with the transfer. Check the name on the evaluation window before you write.

**Writing a one-word observation.** A regression needs at least 10 characters, and a colleague who reads the file later needs more than that.

**Expecting to discharge or admit.** These buttons are not offered to the psychologist. Ask the toxicology manager.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Access denied" page | Your role cannot open that screen | Select the link to your dashboard. |
| "Cannot load the data while offline" | The server cannot be reached | Check the network, then select Retry. |
| Submit Evaluation stays pale | The observation is empty, or too short for a regression | Write the observation. |
| "Only the responsible psychologist of this file can add an evaluation." | You are no longer the referent of this patient, for example after a transfer | Ask the toxicology manager. Do not try again. |
| "This file is read-only for you." | The patient was transferred to a colleague | Read the file only. |
| A red message in the evaluation window | The server refused the evaluation | Read the message, correct, submit once. If it persists, tell the administrator. |
| "PDF export failed. Please try again later." | The PDF could not be produced | Try again once. If it persists, tell the administrator. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Evaluation
: The record of an interview: a decision (maintain, progress, regress), an observation and a recommendation.

Phase
: One of the four stages of the follow-up: Withdrawal, Detox, Reintegration, Aftercare.

Read-only view
: A file opened from the tab Previously followed patients. You can read it but not evaluate, export or change it.

Referent
: The psychologist currently named in the file of a patient, also called the referring psychologist. Named at admission and changed only by a transfer. Only the referent writes evaluations. The name shows in the list and in the printed file.

Relapse
: A regression recorded by an evaluation. It counts in the relapse rate.

Stay
: The period between an admission and a discharge. A readmitted patient has a new stay.

Toxicology Monitoring
: The screen that lists the patients followed, with their phase and their relapses.
