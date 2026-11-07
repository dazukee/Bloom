"""The base class for every screen after login.

A page is a scrolling column (capped at CONTENT_MAX_WIDTH and centred on wide
screens) with a colourful banner holding its title, an optional sentence under
it and actions on the right, then a body. Subclasses set `title` and override
build(). With "Hide decorative art" on, the banner becomes plain text.
"""

from datetime import date

import customtkinter as ctk

from tracker.ui import anim, effects, theme, widgets


class Page(ctk.CTkFrame):
    """One screen in the main area, next to the sidebar."""

    title = ""
    subtitle = ""
    # 3D objects on the banner (see Hero3D) and the banner's own colour.
    banner: list[dict] | None = None
    banner_hue: float | None = None
    banner_height = 128

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
        # Charts animate in when a page is opened, but not when it is prepared
        # unseen in the background (see App._warm_tick) or rebuilt after a save.
        self.animate_art = not getattr(app, "warming", False)
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
        """Return the sentence under the title (the page's key finding)."""
        return self.subtitle

    def build(self) -> None:
        """Create the page's content in self.body; every page overrides this."""

    def hero_hue(self) -> float | None:
        """Return the banner's colour; None means the theme colour (the default)."""
        return self.banner_hue if effects.page_colors else None

    def hero_objects(self) -> list[dict]:
        """Return the banner's art; pages may choose it when they open."""
        return self.banner or []

    def _build_banner(self, head) -> None:
        texts = [(self.heading(), "large_title", "on_primary", 0.03, 0.3, "w")]
        subheading = self.subheading()
        if subheading:
            texts.append((subheading, "body", "on_primary_muted", 0.03, 0.52, "nw"))
        else:
            texts[0] = (self.heading(), "large_title", "on_primary", 0.03, 0.5, "w")
        self.hero = widgets.Hero3D(
            head,
            self.hero_objects(),
            height=self.banner_height,
            texts=texts,
            bg="bg",
            deep=True,
            radius=theme.RADIUS_CARD,
            text_width=0.56,
            hue=self.hero_hue(),
            themed_objects=self.hero_hue() is None,
        )
        self.hero.grid(row=0, column=0, sticky="ew")
        # width/height 1: an empty CTkFrame would otherwise reserve 200 x 200 px.
        self.actions = ctk.CTkFrame(head, width=1, height=1, corner_radius=0)
        self.actions.place(in_=self.hero, relx=1.0, rely=0.5, x=-18, anchor="e")
        self.hero.after_backdrop = self._style_actions

    def _style_actions(self, backdrop) -> None:
        """Give the banner's actions a colour taken from the banner behind them."""
        # After the drawing finishes: their size is only known once laid out.
        self.after_idle(lambda: self._sample_backdrop(backdrop))

    def _sample_backdrop(self, backdrop) -> None:
        try:
            scale = widgets.scaling(self)
            x = self.hero.winfo_width() - 18 * scale - self.actions.winfo_width() / 2
            sample = widgets.render3d.sample(backdrop, x, self.hero.winfo_height() / 2)
            self.actions.configure(fg_color=sample)
            for child in self.actions.winfo_children():
                if hasattr(child, "glass"):
                    child.glass(sample)
        except widgets.tk.TclError:
            pass

    def _build_plain_head(self, head, subheading: str) -> None:
        widgets.label(head, self.heading(), "large_title", "title").grid(
            row=0, column=0, sticky="w"
        )
        if subheading:
            widgets.label(head, subheading, "body", "text_muted", wraplength=640).grid(
                row=1, column=0, sticky="w", pady=(2, 0)
            )
        self.actions = ctk.CTkFrame(head, fg_color="transparent", width=1, height=1)
        self.actions.grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_all(self, progressive: bool = False) -> None:
        """Build the title and body. progressive=True lets cards arrive in turn."""
        head = ctk.CTkFrame(self.column, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, theme.GUTTER + 4))
        head.columnconfigure(0, weight=1)
        if self.banner is not None and not effects.simple_view:
            self._build_banner(head)
        else:
            self._build_plain_head(head, self.subheading())
        self.body = ctk.CTkFrame(self.column, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="ew")
        self.body.columnconfigure(0, weight=1)
        # Cards arrive one by one; with reduce motion they appear all at once,
        # except on a page prepared unseen, where small steps keep clicks quick.
        widgets.progressive_build = progressive and (
            not anim.reduce_motion or not self.animate_art
        )
        try:
            self.build()
        finally:
            widgets.progressive_build = False
        self.built_version = self.app.data_version  # this page shows data up to here
        if hasattr(self, "hero"):
            self.after_idle(self.hero.redraw)

    def refresh(self) -> None:
        """Rebuild the page after a change, keeping the scroll position."""
        position = self.scroll._parent_canvas.yview()[0]
        self.animate_art = False  # the charts just change; no second entrance
        self.column.grid_remove()  # hidden while rebuilt, which is much faster
        for child in self.column.winfo_children():
            child.destroy()
        self._build_all()
        self.column.grid()
        self.after(15, lambda: self.scroll._parent_canvas.yview_moveto(position))

    def save(self, message: str | None = None, tone: str = "good") -> None:
        """Write the user's data to disk and confirm with a toast."""
        self.app.save_user_data()
        if message:
            widgets.toast(self.app, message, tone)

    def ensure_visible(self, widget) -> None:
        """Scroll just enough to show a widget the keyboard reached."""
        canvas = self.scroll._parent_canvas
        try:
            region = canvas.bbox("all")
            total = region[3] - region[1]
            if total <= canvas.winfo_height():
                return
            top = widget.winfo_rooty() - canvas.winfo_rooty()
            bottom = top + widget.winfo_height()
            margin = 24
            if top < margin:
                offset = canvas.canvasy(0) + top - margin
            elif bottom > canvas.winfo_height() - margin:
                offset = canvas.canvasy(0) + bottom - canvas.winfo_height() + margin
            else:
                return
            canvas.yview_moveto(max(offset, 0) / total)
        except widgets.tk.TclError:
            pass

    def spoken(self) -> str:
        """Return the page in words, for reading aloud."""
        return ". ".join(widgets.spoken_text(self.column))

    def _fit_width(self, event) -> None:
        width = event.width / widgets.scaling(self)
        pad = max(theme.PAGE_PAD, (width - theme.CONTENT_MAX_WIDTH) / 2)
        if abs(pad - self._pad) > 1:
            self._pad = pad
            self.column.grid_configure(padx=pad)
