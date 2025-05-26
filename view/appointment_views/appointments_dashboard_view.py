# view/appointment_views/appointments_dashboard_view.py

import customtkinter as ctk
from datetime import date
import calendar

class AppointmentsDashboard(ctk.CTkFrame):
    def __init__(self, master, controller, on_day_selected):
        super().__init__(master)
        self.controller = controller
        self.on_day_selected = on_day_selected 
        today = date.today()
        self.current_year  = today.year
        self.current_month = today.month

        # Navigation mois
        nav = ctk.CTkFrame(self)
        nav.pack(fill="x", pady=5)
        ctk.CTkButton(nav, text="<<", command=self.prev_month).pack(side="left", padx=5)
        self.lbl_month = ctk.CTkLabel(nav, text="")
        self.lbl_month.pack(side="left", expand=True)
        ctk.CTkButton(nav, text=">>", command=self.next_month).pack(side="right", padx=5)
        ctk.CTkButton(nav, text="Today", command=self.go_today).pack(side="right")

        # Grille des jours
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.draw_calendar()

    def draw_calendar(self):
        # Vide l’ancienne grille
        for w in self.grid_frame.winfo_children():
            w.destroy()

        # Titre mois
        month_name = calendar.month_name[self.current_month]
        self.lbl_month.configure(text=f"{month_name} {self.current_year}")

        # En-tête jours
        days = ["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"]
        for col, d in enumerate(days):
            ctk.CTkLabel(self.grid_frame, text=d).grid(row=0, column=col, padx=5, pady=5)

        # Configuration colonnes égales
        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1)

        # Semaines
        calendar.setfirstweekday(calendar.SUNDAY)
        weeks = calendar.monthcalendar(self.current_year, self.current_month)

        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    lbl = ctk.CTkLabel(self.grid_frame, text="")
                    lbl.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                else:
                    dt = date(self.current_year, self.current_month, day)
                    count = len(self.controller.get_by_day(dt))
                    btn = ctk.CTkButton(
                        self.grid_frame,
                        text=f"{day}\n{count} RDV",
                        fg_color="transparent",
                        border_color="blue",
                        text_color="blue",
                        corner_radius=8,
                        command=lambda d=dt: self.on_day_click(d)
                    )
                    btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)

    def on_day_click(self, dt: date):
        # Appelle la vue liste avec la date sélectionnée
        self.on_day_selected(dt)

    def prev_month(self):
        m = self.current_month - 1
        y = self.current_year
        if m < 1:
            m, y = 12, y - 1
        self.current_month, self.current_year = m, y
        self.draw_calendar()

    def next_month(self):
        m = self.current_month + 1
        y = self.current_year
        if m > 12:
            m, y = 1, y + 1
        self.current_month, self.current_year = m, y
        self.draw_calendar()

    def go_today(self):
        t = date.today()
        self.current_year, self.current_month = t.year, t.month
        self.draw_calendar()
