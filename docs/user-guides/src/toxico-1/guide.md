---
title: Admission, phases and evaluations
role: Toxicology manager
subtitle: Admitting a patient to the toxicology programme, following the phases, reading the evaluations written by the psychologist, and opening the patient file.
version: 28 October 2026
output: toxico-1-admission-phases-evaluations
---

## Before you start {.unnumbered}

This guide is for the toxicology manager of the centre. In Glostone-Care the manager runs the intake and the follow-up of the toxicology programme: you admit the patients, you check where each of them stands in the four phases, you read what the psychologist writes after each interview, and you decide, with the promoter, when a stay ends. This first guide covers the admission, the phases, the evaluations and the patient file. Discharge, readmission and the list of discharged patients are in the guide "Toxicology manager 2: discharge, readmission, exports".

The screenshots come from a demonstration installation. The patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the manager can see and do

Your menu has eight entries. **Toxicology Dashboard** and **Toxicology Monitoring** are your daily screens. **Laboratory**, **Lab stock**, **Stock Management**, **Patients**, **Audit & Security** and **System Configuration** are shared with other roles and are not described here, except **Patients**, which holds the full clinical file (chapter 5). The user accounts belong to the administrator alone: the Users screen is not in your menu. Finance is closed to you, and so are the other screens of the administration: if you type the address of such a screen, the application shows an "Access denied" page with a link, [[Go to my dashboard]], back to your dashboard.

You can admit patients, read every file, print the toxicology file of a patient, and discharge. You cannot record an evaluation: that act belongs to the psychologist alone (chapter 4).

A bell at the top right shows notifications. In the demonstration they were laboratory stock alerts, for example a reagent that is almost out. They do not concern patients.

### Interface language

The application starts in French on a new computer. The language switch sits at the top right of every screen: select **EN** to work in English. The choice is kept on that computer.

> Note: Some texts stay in French in English mode. The clinical alerts on the dashboard ("Rechute critique", "Évaluation en retard"), the dates in the patient details window ("26 octobre 2026"), the error message about a consent file that is too large, the comments that the application writes in the history and every printed PDF are in French. The substances are stored as typed, for example "Alcool" and "Cocaïne". The dates in the lists and in the file read day, month, year ("26/10/2026").

### Confidentiality

A toxicology file holds the identity of the patient, a guardian, the consent document and the clinical text written by the psychologist. Do not leave your session open on a shared computer, and select **Logout** at the end of the day. A printed file belongs in the patient folder.

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

The dashboard {1} summarises the whole programme. The four tiles {2} give the active patients, the relapse rate, the patients still in withdrawal (phase 1) and the admissions of the month. **Distribution by Phase** {3} counts the patients in each of the four phases, and **Distribution by Substance** {4} sits beside it. Further down, **Psychologist Workload** shows how many patients each psychologist follows, which helps you balance the next admissions, and **Clinical Alerts** lists the patients who need attention: a relapse has been recorded, or a patient has stayed in phase 1 for longer than the standard period of 15 days.

The figures change as soon as you admit a patient. In the demonstration, two admissions moved the active patients from 13 to 15 and the cannabis and cocaine counts from 1 to 2.

The four tiles count the whole programme and agree with the tiles of the Toxicology Monitoring screen. When the server cannot be reached, the dashboard says "Cannot load the data" with a [[Retry]] button and the tiles read a dash instead of 0.

## The monitoring list and the phases

Select **Toxicology Monitoring** in the menu. This screen is your daily work table.

![The monitoring list](figures/list.png)

The title {1} gives the number of active patients. The tiles repeat the main figures. Each row shows the patient with the code and the substance, the current phase with a coloured bar, the number of relapses, and the referring psychologist. Three buttons end the row: **Details** {5}, **File** {6} and **Discharge** {7}. A fourth button, [[Transfer]], changes the psychologist of the patient (second guide). The tabs {4} switch between **Active** and **Discharged** patients. [[New Toxico Admission]] {3} opens the admission form (chapter 3).

To find a patient, type a name or a patient code in the search box {2}. The list filters itself after a short pause. A search that matches nothing shows "No patient found." Clear the box to see everybody again. The tiles count the whole programme and do not change with the search.

There is no **Evaluate** button on your rows. The psychologist sees one, you do not.

### The four phases

A patient goes through four phases: Phase 1 Withdrawal, Phase 2 Detox, Phase 3 Reintegration and Phase 4 Aftercare. Every admission starts in phase 1, whatever the substance. The bar of a row is red in phase 1, orange in phase 2 and blue in phase 3.

The phase changes only through an evaluation written by the psychologist. An evaluation can keep the patient where he or she is, move the patient to the next phase, or send the patient back one phase, which is recorded as a relapse. You do not move a patient between phases yourself, and neither does the administrator or the promoter. If a patient seems ready to progress, ask the referent psychologist to evaluate.

A red label with the number of relapses appears in the **Relapses** column, and the patient then shows in the Clinical Alerts of the dashboard.

## Admitting a patient

An admission opens the toxicology file of a patient and starts a stay in phase 1. You can admit a person who is already registered in the clinic, for example by the secretary, or a person who is new to the centre. Always search first: attaching an existing patient avoids a second record for the same person.

1. In **Toxicology Monitoring**, select [[New Toxico Admission]], the button at the top right of the list. The window **Admission Form** opens full screen.
2. Type at least two letters of the name, or the code, in the search box. The matching patients appear below with their code and date of birth.

3. Check the code and the date of birth, then select the right line. The search matches part of a name, so two people can share a family name. In the demonstration, "Tchoua" returned two patients with different codes.
4. If nobody matches, select [[New patient]] and go to the section "A patient who is new to the centre" below.

### An existing patient

After you select the patient, his or her name and code appear in a blue band with a [[Change]] button {1}. The application checks at once whether the patient already has a toxicology file.

![The admission form for an existing patient](figures/adm-attach.png)

5. Check the admission date {2}. It opens on today and cannot be in the future.
6. Choose the substance in [[Primary Substance]] {3}: Alcohol, Cannabis, Opioids / Tramadol, Cocaine, Polysubstance Abuse or Other.
7. Choose the psychologist in [[Referral Psychologist]] {4}. The list offers the accounts with the Psychologist role only. This person will follow the patient and will appear on every row and printed file.
8. Type the name and the telephone number of the guardian in [[Guardian Name]] {5} and [[Guardian Contact]]. The guardian is the person to call in an emergency, and both fields are required.
9. Select the signed consent in the upload area {6}: a PDF, PNG or JPG of at most 5 MB. The area then shows the file name. The consent is optional for the application, but the patient file shows "No file attached" without it, so scan the signed form before the interview ends.
10. Write what the team should know in [[Admission Note]]: who referred the patient, the circumstances, the date the consent was signed.
11. Select [[Validate Admission]] {7}.

The button stays pale until the patient, the date, the substance, the psychologist and the two guardian fields are filled. When the admission succeeds, the window closes by itself, a green message "Admission recorded." appears and the new patient appears at the top of the list in phase 1. The tiles move too: in the demonstration, the active patients went from 13 to 14 and **Admissions (month)** from 2 to 3.

### A patient who is new to the centre

Select [[New patient]] and the form adds the identity fields. They open under the substance and the psychologist.

![The admission form for a new patient](figures/adm-new.png)

1. Type the first name {1} and the last name.
2. Choose the date of birth {2}. The latest date offered is ten years before today.
3. Choose the sex in [[Sex]], Male or Female. This field is required and opens on "Select".
4. Type the mother's name {3}. This field is required.
5. The place of residence and the telephone number {4} are optional.
6. Fill the admission date, substance, psychologist, guardian and consent as for an existing patient.
7. Select [[Validate Admission]] {5}.

The application creates the patient and the toxicology file together and gives the patient a code. The file of this patient carries the single label TOXICOLOGY, and its header shows the sex that you chose.

### When the admission is refused

If the patient already has an active toxicology file, a red message says so: "This patient already has an active toxicology file: discharge them first." The button Validate Admission stays inactive. Nothing is created, so close the window. To follow a patient who left earlier, read the guide "Toxicology manager 2", which covers readmission.

A consent file larger than 5 MB is refused with the message "Le fichier est trop volumineux (max 5MB)", in French, and the form stays open. Reduce the scan and select it again. If the server refuses the admission for another reason, a red message appears at the foot of the form and your entries are kept: correct and select Validate Admission once.

## Evaluations

An evaluation is the written result of an interview between the psychologist and the patient. It records one decision about the phase (maintain, progress or regress), the clinical observation and a recommendation. It is the only way to change a phase, and it is the one act in the programme that is reserved to the psychologist, and only to the referent psychologist of the file: the psychologist currently named for the patient. A colleague who does not follow the patient cannot evaluate, and the server refuses the request with the message "Only the responsible psychologist of this file can add an evaluation."

| Action | Psychologist | Toxicology manager | Spiritual counsellor |
|---|---|---|---|
| Record an evaluation | Yes, if referent of the file | No | No |
| Read the evaluations of a patient | Yes | Yes | Yes |
| Admit a patient | No | Yes | No |
| Discharge a patient | No | Yes | No |

The application enforces this. In the demonstration, a request to record an evaluation sent with the manager account was refused by the server, and the Evaluate button is not offered to you. The administrator cannot evaluate either. When a patient changes psychologist (see the guide "Toxicology manager 2"), the new psychologist becomes the only one who can evaluate. Evaluations already written keep the name of their author.

### Reading the evaluations

Open the file of a patient (chapter 5). In the first tab, **Toxico History**, each stay lists its events, the most recent first. An evaluation line shows the date, the decision, the phases before and after, the name of the psychologist, the observation and the recommendation. A regression carries a red **Relapse** label. A line "Psychologist change" appears each time the patient was transferred: it gives the date, the former and the new psychologist, who decided, and the reason. The oldest line of a stay is the admission itself, written "Phase 1: Withdrawal, Admission initiale".

Read the observation and the recommendation before you decide anything about the patient: a request for a family meeting, for example, may need you to call the guardian. To write the evaluation itself, see the psychologist guide, which describes the window, the 500 characters of the observation and the warning on a relapse.

An evaluation cannot be edited or deleted from any screen. If a psychologist chose the wrong decision, the correction is a new evaluation that explains the first one.

## The patient file

Three windows show a patient, from the lightest to the fullest.

### Details

Select [[Details]] on a row. The window shows the identity of the patient, the contact and the address, the substance, the admission date, the psychologist and the current phase.

The window opens on **Identity** and goes on with the contact, the admission and the **Legal guardian**: the name, the contact, the signed consent and the notes written at admission. When a consent was uploaded, the line "Signed consent" offers a link, [[Download the document]], that opens the document in a new browser tab. The document is stored outside the public folders of the server and opens only while you are signed in. Each reading is recorded in the audit log. If it cannot be opened, the window says "Could not open the file. Try again or contact the administrator." [[Open the full file]], at the foot of the window, closes the window and opens the file of the next section.

### File

Select [[File]] on a row. The file opens full screen, with the patient name, the code and the substance at the top, and three tabs.

![The file of a patient](figures/file-history.png)

**Toxico History** {1} shows the progress bar on the four phases, then each stay with its phases and evaluations, and the transfers between psychologists with their reason. A patient who comes back after a discharge starts a second stay, which appears under the first. **Medical Record** {2} lists the last three consultations of the clinic for this patient, and **Prescriptions** {3} the last three prescriptions. When a patient has none, the tab says "No medical record." or "No prescription.".

Both medical tabs carry a [[See full history]] button, which only the manager and the administrator have. It opens the complete clinical file of the patient, described next. Read the medical tabs before a decision on a patient who is also treated for a physical illness: in the demonstration, a patient admitted for cannabis also had a consultation for fever and a prescription for paracetamol, and both appeared here.

At the foot of the window, [[Export record (PDF)]] {4} prints the file (chapter 6), [[Discharge]] {5} starts the discharge described in the second guide, and [[Close the file]] {6} returns to the list.

### The full clinical file

[[See full history]] and the **Patients** entry of the menu open the clinical file of the patient in the same layout as the doctors use.

![The full clinical file](figures/full-file.png)

The header shows the code, the age and the sex, and two labels (CLINICAL, TOXICOLOGY) that say whether the patient is followed by the clinic, in toxicology, or both. The tabs are **Medical Record** {1} with the whole consultation history, **Exams** {2}, **Treatments** {3} and **Toxicology Follow-up** {4}. The last one repeats the substance, the current phase, the psychologist and the admission date. [[Export PDF]] {5} and [[Export Excel]] print or export the clinical file, which is a different document from the toxicology file of chapter 6.

The Treatments tab gives each prescription with its dosage, frequency and duration and a status label (Active, Completed or Cancelled). A laboratory order reads "Lab test request".

## Printing the toxicology file

[[Export record (PDF)]], at the foot of the file window, produces the toxicology file of one patient. Your browser saves it in the download folder.

![The first page of an exported file](figures/export-pdf.png "small")

The printed file carries the header of the centre, the identity of the patient, the referring psychologist, the guardian, each stay with its phases, and the table of evaluations with their date, decision, phases, observation, recommendation and author. At the foot are two signature zones: one for the psychologist and one for the administrative manager, which is where you or the promoter sign. The document is in French whatever the language of the screen.

A printed file contains the clinical text of the evaluations. Keep it in the patient folder and do not leave copies on shared printers. The printed list of discharged patients is described in the second guide.

## Working without a connection

The toxicology screens read their data from the server. They keep no copy on the computer, and an admission cannot be entered offline.

![The list while the computer is offline](figures/offline-list.png "small")

When the computer cannot reach the server, the badge {1} turns yellow and reads "Offline". The application checks the server every 15 seconds, so the badge goes back to "Connected" by itself when the link returns. The list then shows the message "Cannot load the data while offline. Figures shown would not be reliable." {2} with a [[Retry]] button {3} in place of the table, and the tiles read a dash. That is not the real situation: the patients are simply not readable.

The button [[New Toxico Admission]] {4} still opens the form, but the search finds nobody and the list of psychologists is empty, so the form cannot be completed. Keep the information on paper, then reload the page and admit the patient as soon as the connection is back. Before closing the form, check that the patient does not already appear in the list.

## Your profile and password

The account icon at the top right, next to the language switch, opens **My Account**.

![The profile window](figures/account.png "small")

1. Select the account icon.
2. On the **Profile** tab {1}, correct the full name, the e-mail address or the phone number {3}.
3. Select [[Save]] {4}. The message "Profile updated successfully." confirms the change.

The user name and the role cannot be changed here. To change your password, open the **Password** tab {2}, type the current password, then the new one twice, and select [[Save]]. Choose a password of at least 8 characters.

## Common mistakes

**Creating a new patient who already exists.** Search by name and by code first. A second record splits the history of the person in two.

**Choosing the wrong psychologist.** The name you choose is the only person who can evaluate the patient, and it is printed on the file. Check it before you validate. If it is wrong later, use the Transfer button (second guide).

**Looking for the Evaluate button.** It is not offered to your role. Ask the referent psychologist.

**Reading a failed load as "no patient".** After a network cut, the list shows an error message and the tiles read a dash. Select Retry before you draw any conclusion.

**Guessing the sex of a new patient.** The field is required and the file keeps what you chose. Ask the patient or the guardian.

**Forgetting the consent.** The admission goes through without it, and the file then shows "No file attached". Add the scan on the day.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| "Access denied" page | Your role cannot open that screen | Select the link to your dashboard. |
| "Cannot load the data while offline" | The server cannot be reached | Check the network, then select Retry. |
| Validate Admission stays pale | A required field is empty (for a new patient, the sex counts), or the patient already has an active file | Read the red message, fill the fields marked with a star. |
| "This patient already has an active toxicology file" | The patient is already followed | Do not admit again. Open the existing file. |
| "Le fichier est trop volumineux (max 5MB)" | The consent scan is too large | Reduce the scan and select it again. |
| The psychologist list is empty | The server did not answer, or no account has the Psychologist role | Reload the page and open the form again. If it stays empty, tell the administrator. |
| "PDF export failed. Please try again later." | The PDF could not be produced | Try again once. If it persists, tell the administrator. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Admission
: The opening of a toxicology file and of a stay, always in phase 1.

Attach
: Admitting a person who is already registered in the clinic, by selecting the existing record instead of creating a new patient.

Consent
: The signed document in which the patient or the guardian agrees to the programme. It is uploaded at admission.

Evaluation
: The record of an interview: a decision (maintain, progress, regress), an observation and a recommendation. Only the referent psychologist of the file writes it.

Guardian
: The person to call in an emergency. Name and telephone number are required at admission.

Phase
: One of the four stages of the follow-up: Withdrawal, Detox, Reintegration, Aftercare.

Referent psychologist
: The psychologist currently in charge of a patient. Named at admission, changed only by a transfer. Also called referring psychologist.

Relapse
: A regression recorded by an evaluation. It counts in the relapse rate.

Stay
: The period between an admission and a discharge. A readmitted patient has a new stay.
