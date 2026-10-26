---
title: Consultations and prescriptions
role: Doctor
subtitle: Taking a waiting patient in charge, writing the consultation, prescribing, ordering laboratory exams and reading their results, and handling your appointments.
version: 27 October 2026
output: doctor-1-consultations-prescriptions
---

## Before you start {.unnumbered}

This is the first guide for the doctor. It follows a consultation from the moment a nurse sends a patient to you until the prescription and the laboratory result are in the file. It also covers your appointment calendar, what happens when the connection drops, and your own profile. The second doctor guide covers hospitalisation (the Hospitalized Patients screen and the Hospitalization tab of a file): admitting a patient, the stay, the discharge letter and the follow-up of inpatients. Nothing about inpatients is repeated here.

The screenshots come from a demonstration installation. Your screens show the real patients of the centre, but the buttons and fields are the same. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures. The patients in the figures are invented.

### What the doctor can see and do

Your menu has three groups. Under **Activity** you find Appointments, Patients, Hospitalized Patients and Nurse Schedule. Under **Medical** you find Prescriptions, Consultations and Exam Results. Under **Follow-up** you find the Dashboard. A Sync failures entry appears only when something you entered offline was refused by the server.

You work on clinical patients and clinical data. You write consultations and prescriptions, you read laboratory results, and you can export a patient file to PDF or Excel. You do not see invoices or the cash register. You cannot enter or change a laboratory result: that belongs to the laboratory technician. For a patient who is also followed in toxicology or spiritual care, the file tells you that another service follows the patient but does not show the details (see chapter 3).

### Interface language

The application starts in French on a new computer. The language switch sits at the top right of every screen, next to the bell: select **EN** to work in English. The choice is kept on that computer.

> Note: A few texts stay in French in English mode because they come from the reference lists of the centre. The reasons of a consultation (consultation, gratuite, hospitalisation, rendez-vous, suivi_prénatal, urgence) and the laboratory exams, for example "Numération Formule Sanguine", keep their French names, and the interpretation column of a result says "Haut" or "Bas". This guide quotes each label as it appears.

## Signing in and the dashboard

Each member of staff has a personal account. Every consultation and prescription carries the name of the person who saved it.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again.

The application opens on your **Dashboard**.

![The doctor dashboard](figures/dashboard.png)

The menu {1} gives access to every screen of your role. The connection indicator {2} reads "Connected" when the computer is in contact with the server. It can read "Offline" for a few seconds just after you sign in, until the first exchange with the server is done. The block **Patients awaiting review** {3} lists the patients whom a nurse has measured and sent to a doctor. The button [[Take in charge]] {4} claims one of them (chapter 2). **Quick access** {5} opens Appointments, Current stays (inpatients, see the second guide) and Patients. The **Nurse Schedule** entry of the menu is the calendar of nurse shifts and has no step in this guide. The block **Statistics for the period** {6} counts your activity between the two dates at the top right. By default the period covers the recent weeks, up to today.

The statistics need care when you read them. **Consultations performed** counts the consultations saved under your own name. A consultation that a nurse created and that you completed after taking the patient in charge belongs to the nurse's name and is not counted. **Prescriptions** counts those you wrote.

## Taking a waiting patient in charge

A patient who arrives for a consultation first sees a nurse, who measures blood pressure, temperature and weight and writes the first notes. The nurse then switches on **Refer to doctor** in the form. There are two choices. The nurse can name a doctor, and the patient then waits in that doctor's list. Or the nurse can leave the choice on "Shared queue (any doctor)", and every doctor sees the patient until one of them takes the patient in charge.

Your list in **Patients awaiting review** therefore holds the patients named for you and the patients of the shared queue. The oldest wait comes first. Each line shows the patient name, the reason of the visit, the nurse who sent the patient and a small badge for the time spent waiting.

1. On the Dashboard, find the patient in **Patients awaiting review**.
2. Select [[Take in charge]]. The button reserves the patient for you.
3. The patient file opens on the **Medical Record** tab, and the nurse's consultation opens by itself in the edit form, with the measurements and notes already filled in. Behind the form, the consultation now carries the green label "Taken over".

Add your own findings to this same consultation and save it (chapter 4). If you close the form without saving, the two buttons under the consultation are [[Edit]] and [[Prescribe]], as in the figure of chapter 3.

If two doctors select the same patient at almost the same moment, the server accepts the first and answers the second with "This record has already been taken over." The dashboard shows that message in red above the list and removes the line. Nothing is lost: the patient is with the first doctor.

> Caution: Take the patient in charge from the dashboard, then edit the consultation the nurse started. Do not open a new consultation instead. A new consultation closes the nurse's one (see "A consultation can be closed" in chapter 4), and the nurse's measurements stay behind in a read-only record.

A patient who was not sent by a nurse can still be seen: find the patient in **Patients** (chapter 3) and write a consultation from the file.

## The patient file

Open a file from **Patients** with [[View record]], from the dashboard line, or from [[View record]] in an appointment.

The list opens with the newest patients first. Type part of a name or of the patient code in the search box. The tabs above the table count the patients: **All Patients** and **Clinical Care**. You see no toxicology or spiritual tab, because those services belong to other teams. The **Type** column shows NEW for a patient who has no consultation yet, CLINIQUE as soon as a consultation exists, and TOXICO or SPIRITUEL for a patient of another service. Select [[View record]] on a line to open the file.

> Note: The list also offers [[Add a patient]], [[Edit]] and [[Delete]]. Registering patients is the work of the reception desk. Never delete a file that has consultations: ask an administrator.

The file itself has a fixed top part and four tabs.

![The patient file](figures/dossier.png)

The header {1} gives the name, the patient code, the age, the sex and a badge for each service that follows the patient (CLINICAL, TOXICOLOGY, SPIRITUAL). [[Export PDF]] {2} and [[Export Excel]] save the whole file. The four cards show the last blood pressure {3}, weight and temperature, and the known allergies {4}, in red so that nobody misses them. The allergies are the ones written in the most recent consultation, so keep that field up to date.

The tabs are **Medical Record**, **Exams** {5}, **Treatments** and **Hospitalization**. The **Medical Record** tab lists the consultations, the newest first, with the vitals of each one, the notes, the allergies and the history, and the treatment written for it. [[New consultation]] {6} opens an empty consultation form. [[Edit]] {7} and [[Prescribe]] {8} appear under a consultation you are allowed to change. The **Exams** tab is described in chapter 6, and the **Hospitalization** tab belongs to the second guide.

The **Treatments** tab is a short summary of the prescriptions. Each line gives the medicine with its dosage, frequency and duration, then a status label: Active, Completed or Cancelled. A laboratory order appears as "Lab test request" followed by the list of exams. The full list, with the prescriber and the dates, is on the **Prescriptions** screen (chapter 5).

### Patients of other services

A patient can be followed by the clinic and by another service at once. In that case the header shows both badges, and the other service's tab appears in the file. The tab does not open its content to you.

![A patient also followed in toxicology: the tab is closed to the doctor](figures/dossier-restricted.png)

The badge {1} and the tab {2} tell you that the patient is followed elsewhere. The tab answers "This area belongs to another department and is not shown here." {3} Your own consultations and prescriptions for that patient work as usual.

## Writing a consultation

A consultation records one visit: the reason, the vitals, the history and allergies, the symptoms, the diagnosis, the treatment and your notes. There are three ways to reach the form.

- From a patient taken in charge: the nurse's consultation opens by itself, or [[Edit]] under it.
- From a patient file: [[New consultation]] on the **Medical Record** tab.
- From the **Consultations** screen: [[New consultation]] at the top right, where you type the patient code yourself.

![The consultation form, first half](figures/consult-form-a.png)

The form is a panel with these parts, from top to bottom.

**Patient.** The patient code is filled in and locked when you come from a file.

**Consultation.** The date is today. The reason is required: choose it from the list (consultation, gratuite, hospitalisation, rendez-vous, suivi_prénatal, urgence). The severity {1} is Low, Medium or High and colours the line in the consultation list.

**Vitals** {2}. Blood pressure is typed as 120/80. The form refuses a temperature outside 30 to 45 degrees, a weight outside 0 to 1000 kg and a height outside 30 to 250 cm.

**History and allergies** {3}. Write the history and the allergies that apply to this patient. They feed the red allergy card of the file.

**Examination and symptoms** {4}. Describe what you find.

**Diagnosis and treatment** {5}{6}. These two text boxes appear in the list of consultations and in the file.

**Clinical Notes** {7}. Anything else the next doctor should know.

![The consultation form, second half](figures/consult-form-b.png)

Select [[Save]] {8} when the form is complete. The new text appears at once in the file.

When you create a consultation (not when you edit one), the form ends with a section **Doctor referral** and a switch **Refer to doctor**. Leave it off: it exists for the nurse who sends the patient to you.

After you save a new consultation, a green banner offers "Add a prescription for this consultation?" with the buttons [[No]] and [[Yes, prescribe]] below the file. Select [[Yes, prescribe]] to go straight to the prescription form (chapter 5).

### The consultation screen

**Consultations** in the menu lists every consultation with the patient, the date, the reason, the severity, the diagnosis and the treatment.

[[New consultation]] opens the form. The search box finds a patient by name or code, and the filters narrow the list by reason, severity and dates. [[Edit]] changes a consultation and [[Delete]] removes it.

### A consultation can be closed

Only the most recent consultation of a patient can be changed. As soon as a newer one exists for the same patient, the older one becomes read-only: the buttons [[Edit]] and [[Delete]] are replaced by the grey label "Consultation closed: a more recent consultation exists". The prescriptions attached to the older consultation become read-only as well. The rule protects the history: what was true at the time of a visit stays as it was written.

For you, the practical consequence is simple. Finish the writing of a visit before you open another consultation for the same patient, and correct a mistake in the latest consultation, not in an older one. If you need to correct an older one, ask an administrator.

### Starting a consultation from an appointment

The appointment screens have a [[Start consultation]] button (chapter 7). It opens the file of the patient with an empty consultation form already open. Choose the reason, fill in the form as above and save. The appointment is then marked "Completed" by the application, so you do not have to select [[Complete]] afterwards. The reason is not copied from the appointment: choose it yourself.

## Prescriptions

A prescription is either a medicine or a laboratory order. Both are written on the same form and listed on the **Prescriptions** screen.

### Prescribing a medicine

Open the form with [[Prescribe]] under a consultation in the file, with [[Yes, prescribe]] after saving a consultation, or with [[New Prescription]] on the Prescriptions screen. From a consultation, the prescription is linked to that consultation.

![The prescription form for a medicine](figures/presc-form.png)

1. Leave [[This is a lab order]] {1} unticked.
2. Type the medicine in [[Medication]] {2}, for example "Azithromycin 500 mg tablets".
3. Type the [[Dosage]] {3} and the [[Frequency]] ("1 time a day"). Both are required.
4. Type the [[Duration]] {4}, for example "3 days". It is required.
5. Check the [[Start date]] {5}. It is today by default.
6. Fill in the [[End date]] {6} if you want the application to follow the renewal. The field is optional.
7. Add a note for the pharmacist or the patient in [[Notes]] if needed.
8. Select [[Save]] {7}.

The prescription is saved under your user name.

### The Prescriptions screen

[[New Prescription]] opens the form. The search box finds a patient by name or code, and the date filters narrow the list. Each line shows the patient, the medicine with its dose and frequency, the duration, the start date and the end date, then the name of the prescriber. A lab order carries the blue label **Lab order** and lists the exams.

The end date has a coloured label. It shows how many days are left ("In 2 days", in red when the end is close) and reads "Expired" once the date has passed. Use it to find the patients whose treatment must be renewed.

[[Edit]] changes a prescription and [[Delete]] removes it. Both disappear for a prescription whose consultation has been closed by a newer one. A grey label replaces them.

## Laboratory orders and results

### Ordering exams

A laboratory order uses the same form as a medicine.

![A laboratory order, with one exam ticked](figures/lab-order-form.png)

1. Open the prescription form as in chapter 5.
2. Tick [[This is a lab order]] {1}. The medicine fields give way to a list of exams.
3. Type a few letters in the filter {2} to find an exam, for example "Prot".
4. Tick each exam to order {3}. The ticks stay when you change the filter, so you can search for one exam, tick it, then search for the next.
5. Check the date, add a note if needed, and select [[Save]] {4}.

The order appears in the Prescriptions screen as a "Lab order" line. The doctor does not see prices and does not enter the sample or the result: the patient goes to the laboratory, where the technician records the exams and the results.

### Reading the results

**Exam Results** lists the results of the laboratory. It shows only the results that the technician has completed. While an exam is still in progress, you see nothing.

An empty list says "No completed exam found" and "Exams in progress are only visible to the laboratory". Wait for the technician to finish, then select [[Refresh]].

![The completed results of a patient](figures/results-list.png)

1. Select **Exam Results** in the menu.
2. Type a patient name or code in the search box {1}.
3. Select [[Refresh]] {2} to reload the list.
4. Select [[View details]] {3} on a line to read the result, or [[Download PDF]] {4} to save it.

Each line shows the date and the file number, the patient with age and sex, and the exam. A patient who had several exams in one visit has one line per exam, all with the same laboratory code.

![One result in detail](figures/result-detail.png)

The detail shows the result table {1}: the parameter, the value, the unit, the reference values {2} and the interpretation {3}. A value outside the reference range is red with a label High or Low, and the interpretation column says "Haut" or "Bas" (high, low). A note from the technician appears at the bottom as "Conclusion / General notes", and [[Print]] prints the sheet.

The results also appear in the patient file, on the **Exams** tab.

On that tab, each exam has a status label, and a red label such as "2 abnormal" tells you how many values are outside the range. [[View Results]] opens the same detail sheet.

> Note: The reference values come from the laboratory configuration, and the range shown is the one of the patient's sex. When the table shows a dash, the parameter has no reference range for this patient, and the value has no automatic flag. Read it against your own references.

A validated result is locked in the laboratory: the technician can no longer overwrite it. If a value must change, the technician records a correction with a reason. The result then carries the label "Corrected" on the **Exams** tab, and its detail adds a block "Result corrected after validation" with the name of the author, the date, the reason and the value before correction. The doctor who prescribed the exam receives a bell notification, "Result corrected by the laboratory", with the exam, the patient and the reason. Read the corrected value before you rely on the first one.

## Appointments

The **Appointments** screen shows the appointments of the doctors. Nurses and doctors can both book them.

![The appointments list](figures/appointments-list.png)

The list shows the patient, the telephone number, the doctor, the date and time, the reason and the status. Use the search box {1} to find a patient, and the filters on the right to narrow by status (Pending, Cancelled, Completed) and by date (Today, or a chosen day). [[Calendar view]] {2} switches to a month calendar, and [[Book Appointment]] {3} opens the booking form.

### Booking an appointment

1. Select [[Book Appointment]].
2. Type the patient code in [[Patient Code]], then press Tab. The patient name appears under the field when the code is recognised.
3. Choose a specialty, then the doctor. If you leave the doctor empty, the appointment has no assigned doctor.
4. Pick the date and a time slot. The slots run every 30 minutes, from 08:00 to 18:30.
5. Type the reason of the visit if useful.
6. Select [[Save]].

### Working an appointment

In the list view, each line carries five buttons. In the calendar view, select a day that has appointments and a panel opens at the right with the same buttons.

![The day panel of the calendar](figures/appt-day-panel.png)

- [[Start consultation]] {1} opens the patient file with the consultation form open. Write the visit and save: the appointment becomes "Completed".
- [[Complete]] {2} marks the appointment as done without writing a consultation.
- [[View record]] {3} opens the patient file without starting anything.
- [[Edit]] {4} changes the date, the time, the doctor or the reason.
- [[Reject]] {5} cancels the appointment. The application first asks "Reject this appointment? This cannot be undone." Once you confirm, the line shows "Cancelled" with only [[Edit]] left.

A day without appointments opens the booking form with that date already filled in.

When you write the consultation through [[Start consultation]], the appointment closes by itself when you save. For a visit that has no consultation form, select [[Complete]] after the visit. In both cases the status turns to "Completed" and the line keeps only [[Edit]].

> Caution: Select [[Complete]] only for a visit that took place. Once an appointment is Completed or Cancelled, the line keeps only [[Edit]]. If you rejected one by mistake, book a new one.

## Working without a connection

The application keeps working when the internet connection drops. The consultations, prescriptions and appointments you save while offline are kept on the computer and sent to the server when the connection returns.

![A consultation saved while the connection was down](figures/offline-saved.png)

When the network is lost, the indicator {1} turns yellow and reads "Offline (your entries are saved)". The patient file, the Consultations list, the Prescriptions list and the Appointments list still open from the copy on the computer, and a new consultation or prescription is accepted. The new entry {2} appears in the file at once. After a new consultation saved offline, the author may show as "Unknown" and the vitals cards as a dash until the entry has reached the server. The file then reloads those two values by itself within a few seconds of the synchronisation.

Some things need the server and do not work offline.

- The **Dashboard** cannot read the statistics. It shows "Unable to load the statistics." with a [[Try again]] button, and the waiting list shows "Cannot load the data while offline. Figures shown would not be reliable." with a [[Retry]] button instead of "No patient waiting". The list is not empty, it is simply not readable. Taking a patient in charge needs the server.
- In the patient file, the blood pressure, weight and temperature cards show a dash.
- In the patient list, the counters of the tabs show a dash.
- **Exam Results** shows the same message, "Cannot load the data while offline", with a [[Retry]] button. Reading a result needs the server.

When the connection returns, the indicator goes back to green "Connected" within a few seconds and your entries are sent. Check that the entry you made offline is still in the file, then carry on.

If the server refuses an entry once the connection is back, it is listed under **Sync failures** in the menu, with the text you typed so that you can enter it again. This happens, for example, when another computer saved a newer consultation for the same patient while you were offline, because the older one is then closed.

> Caution: Do not clear the browser data, uninstall the browser or switch off the computer for good while the indicator reads "Offline" and entries are waiting. Keep the computer on until it shows "Connected".

## Your profile and password

The account icon at the top right, next to the language switch, opens **My Account**.

![The profile tab](figures/account-profile.png "small")

1. Select the account icon.
2. On the **Profile** tab {1}, correct the full name, the e-mail address or the phone number {3}.
3. Select [[Save]] {4}. The message "Profile updated successfully." confirms the change.

The user name and the role cannot be changed here. To change your password, open the **Password** tab {2}.

1. Type the current password.
2. Type the new password and type it again in the confirmation field.
3. Select [[Save]].

If the current password is wrong, the form answers "The password you entered is incorrect." When the change succeeds, the application signs you out of every session, including the one in use, and you sign in again with the new password. Choose a password of at least 8 characters.

## Common mistakes

**Opening a new consultation instead of editing the nurse's one.** The nurse's record closes and keeps the first measurements as a separate, read-only line. Use [[Edit]] after [[Take in charge]].

**Looking for a result that is not there yet.** Exam Results shows completed exams only. An empty list can mean the laboratory has not finished, not that the order was lost.

**Reading the dashboard offline.** A waiting list that cannot load while the indicator reads "Offline" says nothing about the patients. Wait for "Connected", then select [[Retry]].

**Forgetting to select Complete on an appointment without a consultation.** A visit that you did not write through [[Start consultation]] stays Pending in the calendar until you select [[Complete]].

**Writing allergies in the notes only.** The red allergy card of the file reads the Allergies field of the latest consultation. Write them there.

**Leaving the end date empty on a long treatment.** The prescription then never appears as expiring on the Prescriptions screen.

**Rejecting an appointment by accident.** The confirmation question is the last chance: read the patient and the time before you answer. A rejected appointment cannot be restored.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| Yellow "Offline" indicator | The computer cannot reach the server | Your entries are kept. Wait for "Connected"; tell the administrator if it lasts. |
| "This record has already been taken over." | Another doctor took the patient first | Nothing to do. Choose the next patient. |
| "Unable to load the statistics." or "Cannot load the data while offline" | The dashboard could not reach the server | Select Try again or Retry, or check the connection. |
| "Consultation closed: a more recent consultation exists" | A newer consultation exists for this patient | Work in the newest consultation. Ask an administrator for a correction in an older one. |
| "No completed exam found" | No result is complete yet | Select Refresh later, or ask the laboratory. |
| A red message when saving a consultation | A required field is missing or a vital is out of range | Check the reason, the temperature (30 to 45), the weight and the height. |
| An entry listed under Sync failures | The server refused something entered offline | Open Sync failures, read the reason, enter the text again in the latest consultation. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Claim, take in charge
: To reserve a waiting patient for yourself from the Dashboard. The server accepts the first doctor only.

Closed consultation
: A consultation that has a more recent one for the same patient. It becomes read-only, with its prescriptions.

Lab order
: A prescription for laboratory exams instead of a medicine. It is written on the prescription form with the lab order box ticked.

Patient code
: The code given by the server to every patient file, for example AH2-750903KX.

Refer to doctor
: The switch on the nurse's consultation form that sends the patient to the doctors' waiting list.

Shared queue
: The waiting list that every doctor sees, used when the nurse does not name a doctor.

Sync failures
: The screen that lists entries made offline that the server refused.
