# utils/scrollable_toplevel.py
import tkinter as tk

class ScrollableToplevel(tk.Toplevel):
    """
    Toplevel with a vertical scrollbar and mousewheel support (Windows/Mac + Linux).
    Usage:
        top = ScrollableToplevel(parent, title="Titre", size="900x650")
        form = MyForm(top.form_frame, ...)
        top.grab_set()
    The actual frame to pack/grid the form into is `top.form_frame`.
    """
    def __init__(self, parent, title="Fenêtre", size=None):
        super().__init__(parent)
        if title:
            try:
                self.title(title)
            except Exception:
                pass
        if size:
            try:
                self.geometry(size)
            except Exception:
                pass
        try:
            self.transient(parent.winfo_toplevel())
        except Exception:
            pass

        # container + canvas + scrollbar
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(container, highlightthickness=0)
        self._vscroll = tk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vscroll.set)

        self._vscroll.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # frame qui contiendra le formulaire
        self.form_frame = tk.Frame(self._canvas)
        self._form_window = self._canvas.create_window((0, 0), window=self.form_frame, anchor="nw")

        # redimensionnement / scrollregion
        def _on_frame_config(event):
            try:
                self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            except Exception:
                pass
        self.form_frame.bind("<Configure>", _on_frame_config)

        def _on_canvas_config(event):
            try:
                self._canvas.itemconfig(self._form_window, width=event.width)
            except Exception:
                pass
        self._canvas.bind("<Configure>", _on_canvas_config)

        # Mouse wheel handlers (Windows/Mac and Linux)
        def _on_mousewheel_windows(event):
            # event.delta lisse sur Windows/Mac ; 120 typique
            try:
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _on_button4(event):
            # Linux scroll up
            try:
                self._canvas.yview_scroll(-1, "units")
            except Exception:
                pass

        def _on_button5(event):
            # Linux scroll down
            try:
                self._canvas.yview_scroll(1, "units")
            except Exception:
                pass

        # Bind globalement pour que la molette fonctionne même si le focus est sur widgets internes.
        # On conserve les bindings et on nettoie à la fermeture.
        self._bound = False
        try:
            self.bind_all("<MouseWheel>", _on_mousewheel_windows)
            self.bind_all("<Button-4>", _on_button4)  # Linux scroll up
            self.bind_all("<Button-5>", _on_button5)  # Linux scroll down
            self._bound = True
        except Exception:
            # si bind_all échoue, on ignore (ne doit pas planter)
            self._bound = False

        # S'assurer de nettoyer les bindings quand la fenêtre est détruite
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _cleanup_bindings(self):
        if self._bound:
            try:
                self.unbind_all("<MouseWheel>")
                self.unbind_all("<Button-4>")
                self.unbind_all("<Button-5>")
            except Exception:
                pass
            self._bound = False

    def _on_close(self):
        # cleanup + destroy
        try:
            self._cleanup_bindings()
        except Exception:
            pass
        try:
            super().destroy()
        except Exception:
            try:
                self.destroy()
            except Exception:
                pass
