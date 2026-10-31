# Staff adoption kit

Use the files in this order. Everything is in English. Names, phones and dates are in square brackets to fill.

1. `announcement-message.md`: announcement, short message, session reminder and FAQ. Send before week 0.
2. `training-and-pilot-plan.md` and `.pdf`: objectives, roles, weekly schedule, training, risks, go or no-go.
3. `adoption-tracking.xlsx`: weekly indicators, issues log, attendance, go or no-go. Fill every week.
4. `one-pagers/<role>.md` and `.pdf`: one A4 sheet per role. Hand out at the training session.
5. `outage-sheet.md` and `.pdf`: one page to stick near each workstation before go-live.
6. Rebuild the PDFs with `python docs/adoption/build_adoption_pdfs.py` after editing a Markdown file.
7. Check the "to confirm" points in the plan (section 10) before the pilot.
8. Source of truth for screens: `docs/user-guides/`.
