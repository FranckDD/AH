from typing import Any, Callable, List, Dict
from datetime import date
import calendar
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from view_pyqt6.controller_resolver import ControllerResolver
from datetime import date, datetime

class AppointmentsDashboardView(QWidget):
    def __init__(self, parent, controllers: Any, on_day_selected: Callable[[date], None] = None):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        try:
            self.appt_ctrl = self.resolver.appointment_controller()
        except Exception:
            self.appt_ctrl = None
        self.on_day_selected = on_day_selected

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        # cache monthly appointments: map 'YYYY-MM-DD' -> list
        self._month_appts_map: Dict[str, List] = {}

        self._build_ui()
        QTimer.singleShot(30, self.draw_calendar)

    def _build_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        # header + legend
        header = QHBoxLayout()
        title = QLabel("Calendrier des Rendez-vous")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        legend = QHBoxLayout()
        legend.addWidget(self._legend_item("#e9ecef", "0"))
        legend.addWidget(self._legend_item("#e6ffef", "1-2"))
        legend.addWidget(self._legend_item("#fff4e6", "3-5"))
        legend.addWidget(self._legend_item("#ffe6e6", "6+"))
        header.addLayout(legend)
        root.addLayout(header)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("◀"); self.btn_prev.setFixedWidth(36); self.btn_prev.clicked.connect(self.prev_month)
        self.btn_next = QPushButton("▶"); self.btn_next.setFixedWidth(36); self.btn_next.clicked.connect(self.next_month)
        self.btn_today = QPushButton("Aujourd'hui"); self.btn_today.clicked.connect(self.go_today)
        self.lbl_month = QLabel("")
        self.lbl_month.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_month.setFont(QFont("", 12, QFont.Weight.Bold))
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.lbl_month, stretch=1)
        nav.addWidget(self.btn_next)
        nav.addWidget(self.btn_today)
        root.addLayout(nav)

        self.cal_frame = QFrame()
        self.cal_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.cal_frame.setStyleSheet("QFrame { background: white; border: 1px solid #e9ecef; border-radius: 6px; }")
        self.cal_layout = QVBoxLayout(self.cal_frame)
        self.cal_layout.setContentsMargins(10, 10, 10, 10)
        root.addWidget(self.cal_frame, stretch=1)

        # grid placeholder
        self.grid_widget = QWidget()
        self.cal_layout.addWidget(self.grid_widget)

    def _legend_item(self, color_hex: str, text: str):
        w = QLabel(text)
        w.setFixedHeight(20)
        w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w.setStyleSheet(f"background:{color_hex}; border-radius:4px; padding:2px 6px; border:1px solid #ddd;")
        return w

    def draw_calendar(self):
        # clear existing grid layout
        try:
            old_layout = self.grid_widget.layout()
            if old_layout:
                while old_layout.count():
                    it = old_layout.takeAt(0)
                    w = it.widget()
                    if w:
                        w.deleteLater()
                old_layout.deleteLater()
        except Exception:
            pass

        from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget
        grid = QGridLayout()
        grid.setSpacing(8)
        self.grid_widget.setLayout(grid)

        month_name = calendar.month_name[self.current_month]
        self.lbl_month.setText(f"{month_name} {self.current_year}")

        weekday_names = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]
        for col, d in enumerate(weekday_names):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color:#444; font-weight:600;")
            grid.addWidget(lbl, 0, col)

        calendar.setfirstweekday(calendar.SUNDAY)
        weeks = calendar.monthcalendar(self.current_year, self.current_month)

        # fetch month appointments once
        first_day = date(self.current_year, self.current_month, 1)
        last_day = date(self.current_year, self.current_month, calendar.monthrange(self.current_year, self.current_month)[1])
        self._load_month_appointments(first_day, last_day)

        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    placeholder = QLabel("")
                    placeholder.setFixedHeight(80)
                    placeholder.setStyleSheet("background:transparent;")
                    grid.addWidget(placeholder, r, c)
                    continue
                dt = date(self.current_year, self.current_month, day)
                dw = self._build_day_widget(dt)
                grid.addWidget(dw, r, c)

    def _load_month_appointments(self, first_day: date, last_day: date):
        # build key
        key = f"{first_day.isoformat()}_{last_day.isoformat()}"
        try:
            # call once per draw
            if self.appt_ctrl and hasattr(self.appt_ctrl, "list_appointments"):
                raw = self.appt_ctrl.list_appointments(
                    page=1, per_page=1000,
                    date_from=first_day.isoformat(),
                    date_to=last_day.isoformat()
                )
                #print(f"[DEBUG] Raw response from list_appointments: {type(raw)} - {raw}")
            else:
                raw = []
        except Exception as e:
            #print("[DEBUG] load_month_appointments error:", e)
            raw = []

        # normalize into a list of items
        items = []
        if isinstance(raw, dict) and "data" in raw:
            #print(f"[DEBUG] Raw response keys: {list(raw.keys())}")
            items = raw["data"] or []
        elif isinstance(raw, list):
            #print(f"[DEBUG] Raw response keys: {list(raw.keys())}")
            items = raw
        elif "items" in raw:  # Ensuite "items"
            #print(f"[DEBUG] Items count: {len(raw.get('items', []))}")
            items = raw["items"] or []
        elif "results" in raw:  # Puis "results"
            #print(f"[DEBUG] Data count: {len(raw.get('data', []))}")
            items = raw["results"] or []    
        else:
            try:
                items = list(raw or [])
            except Exception:
                items = []


        # helper to get YYYY-MM-DD from various types
        def _to_iso_date_str(val):
            if val is None:
                return None
            # already a date (but not datetime)
            if isinstance(val, date) and not isinstance(val, datetime):
                return val.isoformat()
            # datetime -> date -> iso
            if isinstance(val, datetime):
                return val.date().isoformat()
            # string: try iso parse then fallback to first 10 chars
            if isinstance(val, str):
                s = val.strip()
                # try parse full ISO (handles "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS")
                try:
                    dt = datetime.fromisoformat(s)
                    return dt.date().isoformat()
                except Exception:
                    # last resort: take YYYY-MM-DD at start
                    if len(s) >= 10:
                        return s[:10]
                    return s
            # unknown type: try str and cut first 10 chars
            try:
                s = str(val)
                if len(s) >= 10:
                    return s[:10]
                return s
            except Exception:
                return None

        # build map (normalized keys => list)
        self._month_appts_map.clear()
        for a in items:
            try:
                if isinstance(a, dict):
                    ad = a.get("appointment_date") or a.get("date") or a.get("appointment_datetime")
                else:
                    ad = getattr(a, "appointment_date", None) or getattr(a, "date", None)
                day_iso = _to_iso_date_str(ad)
                if not day_iso:
                    continue
                lst = self._month_appts_map.setdefault(day_iso, [])
                lst.append(a)
            except Exception as e:
                # safe guard: don't break loop on malformed item
                #print("[DEBUG] _load_month_appointments item parse error:", e)
                continue

    def _build_day_widget(self, dt: date):
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
        w = QWidget()
        w.setMinimumHeight(90)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        day_lbl = QLabel(str(dt.day))
        day_lbl.setStyleSheet("font-weight:700;")
        layout.addWidget(day_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        day_key = dt.isoformat()
        appts = self._month_appts_map.get(day_key, []) or []
        count = len(appts)

        if count == 0:
            color = "#e9ecef"; text_color = "#666"
        elif count <= 2:
            color = "#e6ffef"; text_color = "#1b5e20"
        elif count <= 5:
            color = "#fff4e6"; text_color = "#6a3e00"
        else:
            color = "#ffe6e6"; text_color = "#8b0000"

        badge = QLabel(f"{count} RDV")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background:{color}; color:{text_color}; border-radius:6px; padding:4px; font-weight:600;")
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)

        # tooltip
        tooltip_lines = []
        try:
            for a in appts[:8]:
                if isinstance(a, dict):
                    t = a.get("appointment_time") or a.get("time") or ""
                    p = a.get("patient") or {}
                    pcode = p.get("code_patient", "") if isinstance(p, dict) else ""
                    pname = f"{p.get('first_name','')} {p.get('last_name','')}".strip() if isinstance(p, dict) else ""
                else:
                    t = getattr(a, "appointment_time", "")
                    p = getattr(a, "patient", None)
                    pcode = getattr(p, "code_patient", "") if p else ""
                    pname = (getattr(p, "first_name", "") + " " + getattr(p, "last_name", "")).strip() if p else ""
                tooltip_lines.append(f"{t} — {pcode} {pname}")
        except Exception:
            pass
        tooltip = "\n".join(tooltip_lines) if tooltip_lines else f"{count} rendez-vous"
        w.setToolTip(tooltip)

        btn = QPushButton("Voir")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(26)
        btn.clicked.connect(lambda _, d=dt: self._on_day_clicked(d))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignBottom)

        w.setStyleSheet("QWidget{border:1px solid rgba(0,0,0,0.04); border-radius:6px; padding:4px;} QWidget:hover{background: #fbfbfb;}")

        return w

    def _on_day_clicked(self, dt: date):
        if callable(self.on_day_selected):
            try:
                self.on_day_selected(dt)
            except Exception:
                pass

    def prev_month(self):
        m = self.current_month - 1; y = self.current_year
        if m < 1: m, y = 12, y-1
        self.current_month, self.current_year = m, y
        self.draw_calendar()

    def next_month(self):
        m = self.current_month + 1; y = self.current_year
        if m > 12: m, y = 1, y+1
        self.current_month, self.current_year = m, y
        self.draw_calendar()

    def go_today(self):
        t = date.today()
        self.current_year, self.current_month = t.year, t.month
        self.draw_calendar()