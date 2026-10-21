# utils/lab_stock_rules.py
"""Seuils metier du stock labo."""

# Un lot expirant dans moins de ce nombre de jours declenche une alerte de peremption.
EXPIRY_WARNING_DAYS = 60
# Un comptage plus ancien que ce nombre de jours declenche un rappel.
COUNT_REMINDER_DAYS = 7
