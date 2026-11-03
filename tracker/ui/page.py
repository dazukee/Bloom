"""The base class for every screen after login.

A page is a scrolling column (capped at CONTENT_MAX_WIDTH and centred on wide
screens) with a large title, an optional grey sentence under it, actions on
the right, and a body. Subclasses set `title` and override build().
"""

from datetime import date

import customtkinter as ctk

from tracker.ui import anim, theme, widgets


class Page(ctk.CTkFrame):
    """One screen in the main area, next to the sidebar."""

    title = ""
    subtitle = ""
    # 3D objects for a purple banner in place of the plain title (see Hero3D).
    banner: list[dict] | None = None

    def __init__(self, app, host) -> None:
        super().__init__(host, fg_color=theme.pair("bg"), corner_radius=0)
        self.app = app
        self.today = date.today()
        self._pad = theme.PAGE_PAD
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.pair("bg"),
            corner_radius=0,
            scrollbar_button_color=theme.pair("border"),
            scrollbar_button_hover_color=theme.pair("text_muted"),
        )
        self.scroll.pack(fill="both", expand=True)
        self.scroll.columnconfigure(0, weight=1)
        widgets.fast_scroll(self.scroll)
        self.column = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.column.grid(
            row=0, column=0, sticky="ew", padx=self._pad, pady=(24, theme.PAGE_PAD)
        )
        self.column.columnconfigure(0, weight=1)
        self.scroll._parent_canvas.bind("<Configure>", self._fit_width, add="+")
        self._build_all(progressive=True)

    @property
    def data(self) -> dict:
        """The logged-in user's data."""
        return self.app.user_data

    @property
    def settings(self) -> dict:
        """The user's preferences (units, appearance...)."""
        return self.app.user_data["settings"]

    def heading(self) -> str:
        """Return the page title; pages may personalise it."""
        return self.title

    def subheading(self) -> str:
        """Return the grey sentence under the title (the page's key finding)."""
        return self.subtitle

    def build(self) -> None:
        """Create the page's content in self.body; every page overrides this."""

    def _build_all(self, progressive: bool = False) -> None:
        """Build the title and body. progressive=True lets cards arrive in turn."""
        head = ctk.CTkFrame(self.column, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, theme.GUTTER + 4))
        head.columnconfigure(0, weight=1)
        subheading = self.subheading()
        if self.banner:
            texts = [(self.heading(), "large_title", "on_primary", 0.04, 0.4, "w")]
            if subheading:
                texts.append((subheading, "body", "on_primary_muted", 0.04, 0.66, "w"))
            widgets.Hero3D(
                head, self.banner, height=150, texts=texts, bg="bg", deep=True,
                radius=theme.RADIUS_CARD, text_width=0.6,
            ).grid(row=0, column=0, rowspan=2, sticky="ew")  # fmt: skip
        else:
            widgets.label(head, self.heading(), "large_title", "title").grid(
                row=0, column=0, sticky="w"
            )
        if subheading and not self.banner:
            widgets.label(head, subheading, "body", "text_muted", wraplength=640).grid(
                row=1, column=0, sticky="w", pady=(2, 0)
            )
        # width/height 1: an empty CTkFrame would otherwise reserve 200 x 200 px.
        self.actions = ctk.CTkFrame(head, fg_color="transparent", width=1, height=1)
        self.actions.grid(row=0, column=1, rowspan=2, sticky="e")
        self.body = ctk.CTkFrame(self.column, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="ew")
        self.body.columnconfigure(0, weight=1)
        widgets.progressive_build = progressive and not anim.reduce_motion
        try:
            self.build()
        finally:
            widgets.progressive_build = False
        self.built_version = self.app.data_version  # this page shows data up to here

    def refresh(self) -> None:
        """Rebuild the page after a change, keeping the scroll position."""
        position = self.scroll._parent_canvas.yview()[0]
        for child in self.column.winfo_children():
            child.destroy()
        self._build_all()
        self.after(15, lambda: self.scroll._parent_canvas.yview_moveto(position))

    def save(self, message: str | None = None, tone: str = "good") -> None:
        """Write the user's data to disk and confirm with a toast."""
        self.app.save_user_data()
        if message:
            widgets.toast(self.app, message, tone)

    def _fit_width(self, event) -> None:
        width = event.width / widgets.scaling(self)
        pad = max(theme.PAGE_PAD, (width - theme.CONTENT_MAX_WIDTH) / 2)
        if abs(pad - self._pad) > 1:
            self._pad = pad
            self.column.grid_configure(padx=pad)
