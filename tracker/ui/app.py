"""The main window: login, onboarding, the adaptive sidebar and page transitions.

What a screen may use (the contract between app.py and every page):
    app.users, app.user, app.user_data       accounts, the session, its data
    app.save_users(), app.save_user_data()   write them to disk
    app.delete_user_files()                  remove the user's data file
    app.log_in(user), app.log_out()          start or end a session
    app.show_login(), show_register(), show_reset(), show_code(...)
    app.show_page(name)                      open a sidebar page (keys of PAGES)
    app.enter_main(page)                     show the sidebar layout
    app.apply_settings(rebuild=True)         re-apply look, motion and sound
    app.read_page(), app.open_quick_find()   read aloud; search everything
"""

import ctypes
import sys
import threading
import time
import tkinter as tk
import traceback
from datetime import date
from pathlib import Path
from tkinter import messagebox
from types import TracebackType

import customtkinter as ctk

from tracker import daylog, garden, insights, profile, storage
from tracker.ui import (
    anim,
    effects,
    icons,
    palette,
    render3d,
    sfx,
    speech,
    theme,
    widgets,
)
from tracker.ui.activity_page import ActivityPage
from tracker.ui.auth_pages import CodeScreen, LoginScreen, RegisterScreen, ResetScreen
from tracker.ui.bbt_page import BbtPage
from tracker.ui.bmi_page import BmiPage
from tracker.ui.cycle_page import CyclePage
from tracker.ui.garden_page import GardenPage
from tracker.ui.home_page import HomePage
from tracker.ui.journal_page import JournalPage
from tracker.ui.nutrition_page import NutritionPage
from tracker.ui.onboarding import Onboarding
from tracker.ui.settings_page import SettingsPage
from tracker.ui.vitals_page import VitalsPage

# Sidebar groups: (group label, [(page key, label, icon, page class), ...])
NAV = [
    (
        "",
        [
            ("home", "Today", "home", HomePage),
            ("garden", "My Garden", "sparkle", GardenPage),
        ],
    ),
    (
        "Body",
        [
            ("cycle", "Cycle", "drop", CyclePage),
            ("bbt", "Temperature", "thermometer", BbtPage),
            ("journal", "Journal", "journal", JournalPage),
        ],
    ),
    (
        "Health",
        [
            ("vitals", "Vitals & Sleep", "heart", VitalsPage),
            ("activity", "Activity", "activity", ActivityPage),
            ("nutrition", "Nutrition", "leaf", NutritionPage),
            ("bmi", "BMI", "gauge", BmiPage),
        ],
    ),
]
SETTINGS_ITEM = ("settings", "Settings", "gear", SettingsPage)
CYCLE_PAGES = {"cycle", "bbt"}  # hidden when cycle tracking is off
PAGES = {key: page for _, items in NAV for key, _, _, page in items}
PAGES["settings"] = SettingsPage
ORDER = [key for _, items in NAV for key, _, _, _ in items] + ["settings"]
# The accent each cycle phase uses with the "Follow my cycle" theme.
PHASE_ACCENTS = {
    "menstrual": "rose",
    "follicular": "forest",
    "ovulation": "coral",
    "luteal": "bloom",
}
TEXT_SIZES = {"small": 0.92, "default": 1.0, "large": 1.12, "xlarge": 1.26}
# Pages are prepared in the background after this long without a click or key.
WARM_IDLE_S = 1.2
WARM_CHECK_MS = 400
MAX_WAITING_PAGES = 12  # old hidden pages kept for destroying in quiet moments
TEXT_SIZE_ORDER = list(TEXT_SIZES)
ICON_FILE = Path(__file__).resolve().parent.parent.parent / "assets" / "bloom.ico"
DWM_CAPTION_COLOR = 35  # Windows 11 only; older systems ignore the request
DWM_TEXT_COLOR = 36


def _shorten(text: str, limit: int) -> str:
    """Fit a name in the sidebar: first word if too long, then cut with an ellipsis."""
    if len(text) > limit and " " in text:
        text = text.split()[0]
    return text if len(text) <= limit else text[: limit - 1] + "…"


class Sidebar(ctk.CTkFrame):
    """Labelled navigation (or an icon rail on narrow windows) with the account.

    The list scrolls if it cannot fit (very large text on a small screen), so the
    search box and the account always stay in view.
    """

    def __init__(self, app, compact: bool) -> None:
        width = theme.RAIL_WIDTH if compact else theme.SIDEBAR_WIDTH
        super().__init__(
            app, fg_color=theme.pair("sidebar"), corner_radius=0, width=width
        )
        self.grid_propagate(False)
        self.app = app
        self.compact = compact
        self.items: dict[str, ctk.CTkButton] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        track_cycle = app.user_data["profile"]["track_cycle"]

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=12, pady=(14, 8))
        logo = ctk.CTkImage(render3d.logo(96), size=(36, 36))
        ctk.CTkLabel(brand, text="", image=logo).grid(row=0, column=0, rowspan=2)
        if not compact:
            widgets.label(brand, theme.APP_NAME, "title3", "sidebar_text").grid(
                row=0, column=1, sticky="sw", padx=(8, 0)
            )
            widgets.label(brand, "Health Tracker", "caption", "sidebar_muted").grid(
                row=1, column=1, sticky="nw", padx=(8, 0)
            )
        self._search_box()

        self.nav = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.pair("sidebar"),
            corner_radius=0,
            width=width - 8,
            scrollbar_button_color=theme.pair("sidebar"),
            scrollbar_button_hover_color=theme.pair("sidebar_hover"),
        )
        self.nav.grid(row=2, column=0, sticky="nsew")
        self.nav._scrollbar.grid_remove()
        self.nav.columnconfigure(0, weight=1)
        widgets.fast_scroll(self.nav)

        row = 0
        for group, entries in NAV:
            if group and not compact:
                widgets.label(self.nav, group, "footnote", "sidebar_muted").grid(
                    row=row, column=0, sticky="w", padx=14, pady=(8, 2)
                )
                row += 1
            elif group:
                ctk.CTkFrame(
                    self.nav, height=1, fg_color=theme.pair("sidebar_hover")
                ).grid(row=row, column=0, sticky="ew", padx=14, pady=6)
                row += 1
            for key, text, icon_name, _ in entries:
                if key in CYCLE_PAGES and not track_cycle:
                    continue
                self._item(row, key, text, icon_name)
                row += 1
        self._item(row, *SETTINGS_ITEM[:3])
        self._account(3)

        self.marker = ctk.CTkFrame(
            self.nav,
            width=4,
            height=22,
            corner_radius=2,
            fg_color=theme.pair("sidebar_marker"),
        )
        self.marker_y = None

    def _search_box(self) -> None:
        """A button that looks like a search box and opens Quick Find."""
        box = ctk.CTkButton(
            self,
            text="" if self.compact else "Find anything",
            image=icons.icon("search", 16, "sidebar_muted"),
            compound="left",
            anchor="center" if self.compact else "w",
            height=theme.control_height(32),
            corner_radius=10,
            font=theme.font("footnote"),
            fg_color=theme.pair("sidebar_hover"),
            hover_color=theme.pair("sidebar_active"),
            text_color=theme.pair("sidebar_muted"),
            command=self.app.open_quick_find,
        )
        box.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        widgets.keyboard(box, box.invoke, "Quick Find, button")
        widgets.Tooltip(box, "Find any page, setting or action (Ctrl+K)")

    def _item(self, row: int, key: str, text: str, icon_name: str) -> None:
        item = ctk.CTkButton(
            self.nav,
            text="" if self.compact else text,
            image=icons.icon(icon_name, 20, "sidebar_muted"),
            compound="left",
            anchor="center" if self.compact else "w",
            height=theme.control_height(38),
            corner_radius=10,
            font=theme.font("body"),
            fg_color="transparent",
            hover_color=theme.pair("sidebar_hover"),
            text_color=theme.pair("sidebar_text"),
            command=sfx.with_sound(lambda k=key: self.app.show_page(k), "nav"),
        )
        item.grid(row=row, column=0, sticky="ew", padx=6, pady=1)
        item.icon_name = icon_name
        if self.compact:
            widgets.Tooltip(item, text)
        widgets.keyboard(item, item.invoke, f"{text}, page")
        self.items[key] = item

    def _account(self, row: int) -> None:
        name = (
            self.app.user_data["profile"]["display_name"] or self.app.user["username"]
        )
        tint = "transparent" if self.compact else theme.pair("sidebar_hover")
        box = ctk.CTkFrame(self, fg_color=tint, corner_radius=14)
        box.grid(
            row=row,
            column=0,
            sticky="ew" if not self.compact else "",
            padx=10,
            pady=(6, 12),
        )
        box.columnconfigure(1, weight=1)
        # Today's flower stands in for a photo: it fills up as the day goes on.
        self.flower = ctk.CTkLabel(box, text="", cursor="hand2")
        self.flower.grid(row=0, column=0, rowspan=2, padx=(6, 6), pady=6)
        self.flower.bind("<Button-1>", lambda _e: self.app.show_page("garden"))
        self.flower_tip = widgets.Tooltip(self.flower, "")
        self.petal_text = None
        if not self.compact:
            widgets.label(box, self._fitted(name), "headline", "sidebar_text").grid(
                row=0, column=1, sticky="sw"
            )
            self.petal_text = widgets.label(box, "", "caption", "sidebar_muted")
            self.petal_text.grid(row=1, column=1, sticky="nw")
            logout = ctk.CTkButton(
                box,
                text="",
                image=icons.icon("logout", 18, "sidebar_text"),
                width=32,
                height=theme.control_height(32),
                corner_radius=theme.RADIUS_CONTROL,
                fg_color="transparent",
                hover_color=theme.pair("sidebar"),
                command=sfx.with_sound(self.app.confirm_log_out, "click"),
            )
            logout.grid(row=0, column=2, rowspan=2, padx=(0, 4))
            widgets.Tooltip(logout, "Log out")
            widgets.keyboard(logout, logout.invoke, "Log out, button")
        self.refresh_flower()

    @staticmethod
    def _fitted(name: str, room: int = 106) -> str:
        """Fit a name in the account box, whatever the font's width."""
        font = theme.font("headline")
        text = _shorten(name, 18)
        if font.measure(text) > room and " " in text:
            text = text.split()[0]
        while font.measure(text) > room and len(text) > 2:
            text = text[:-2] + "…"
        return text

    def refresh_flower(self) -> None:
        """Show today's petals on the small flower and beside the name."""
        data = self.app.user_data
        log = daylog.peek_day(data, date.today())
        done = [earned for _, earned in garden.petals(log, data["goals"])]
        art = widgets.flower_image(84, done)
        # Faint petals would vanish on the dark panel, so they sit on a soft disc.
        self.flower.configure(image=ctk.CTkImage(art, size=(40, 40)))
        count = sum(done)
        words = f"{count} of {garden.TOTAL_PETALS} petals today"
        if self.petal_text is not None:
            self.petal_text.configure(text=f"{count} of {garden.TOTAL_PETALS} petals")
        self.flower_tip.text = f"{words}. Open My Garden."

    def select(self, key: str) -> None:
        """Highlight the current page and glide the marker to it."""
        for name, item in self.items.items():
            active = name == key
            item.configure(
                fg_color=theme.pair("sidebar_active") if active else "transparent",
                hover_color=theme.pair("sidebar_active" if active else "sidebar_hover"),
                text_color=theme.pair(
                    "sidebar_active_text" if active else "sidebar_text"
                ),
                font=theme.font("headline" if active else "body"),
                image=icons.icon(
                    item.icon_name,
                    20,
                    "sidebar_active_text" if active else "sidebar_muted",
                ),
            )
        item = self.items.get(key)
        if item is None:
            self.marker.place_forget()
            return
        self.after(20, lambda: self._move_marker(item))

    def _move_marker(self, item) -> None:
        try:
            if item.winfo_height() < 2:  # not laid out yet: try again shortly
                self.after(30, lambda: self._move_marker(item))
                return
            scale = widgets.scaling(self)
            target = (item.winfo_y() + item.winfo_height() / 2) / scale - 11
        except tk.TclError:
            return
        start = self.marker_y if self.marker_y is not None else target
        self.marker_y = target

        def step(t: float) -> None:
            self.marker.place(x=1, y=anim.lerp(start, target, t))

        anim.animate(
            self.marker, theme.BASE + 60, step, ease=anim.spring, key="nav-marker"
        )


class App(ctk.CTk):
    """The main window; one instance runs for the whole program."""

    def __init__(self, data_dir=storage.DATA_DIR) -> None:
        super().__init__()
        theme.load_font_files()
        theme.reset_fonts()
        self.tk.eval(
            # A timer can outlive a closed page; that is harmless, so stay quiet.
            'proc bgerror {message} {if {![string match "invalid command name*" '
            "$message]} {catch {puts stderr $message}}}"
        )
        icons.reset_cache()
        ctk.set_appearance_mode("system")
        self.data_dir = data_dir
        self.title(f"{theme.APP_NAME} · {theme.APP_TAGLINE}")
        self.configure(fg_color=theme.pair("bg"))
        self._place_window()
        self.minsize(860, 560)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.users: dict = storage.new_users()
        self.user: dict | None = None
        self.user_data: dict | None = None
        self.screen = None
        self.sidebar: Sidebar | None = None
        self.host = None
        self.page = None
        self.pages: dict = {}  # built pages, kept for instant return visits
        self.data_version = 0  # goes up on every save, so stale pages rebuild
        self.bloomed_on = None  # the day the full-bloom celebration last ran
        self.text_scale = 1.0
        self.current = "home"
        self.compact = False
        self._resize_job = None
        self._shown_mode = ctk.get_appearance_mode()
        self._warm = None  # the page being prepared in the background, if any
        self._warm_since = 0.0  # when it was started
        self._doomed: list = []  # hidden pages waiting to be destroyed
        self.warming = False  # True while that page is being created
        self._last_input = self._last_tick = time.monotonic()
        self.bind("<Configure>", self._on_resize)
        for number in range(1, 10):
            self.bind(f"<Control-Key-{number}>", lambda _e, n=number: self._shortcut(n))
        self.bind("<Control-Key-0>", lambda _e: self._shortcut(10))
        for key, action in (
            ("<Control-k>", self.open_quick_find),
            ("<Control-K>", self.open_quick_find),
            ("<F1>", self.show_help),
            ("<F2>", self.read_page),
            ("<F6>", self.jump_focus),
            ("<F11>", self.toggle_full_screen),
            ("<Escape>", self._escape),
            ("<Control-equal>", lambda: self.change_text_size(1)),
            ("<Control-plus>", lambda: self.change_text_size(1)),
            ("<Control-minus>", lambda: self.change_text_size(-1)),
        ):
            self.bind(key, lambda _e, run=action: run())
        self.bind("<Button-1>", self._click_away, add="+")
        # Any key or click means "busy": pages are only prepared in quiet moments.
        for sequence in ("<KeyPress>", "<ButtonPress>", "<Button-1>", "<MouseWheel>"):
            self.bind(sequence, self.note_input, add="+")
        self.after(WARM_CHECK_MS, self._warm_tick)
        self.dress_window(self)
        self._art_thread = threading.Thread()  # replaced in start()
        self.start()

    # The window itself ------------------------------------------------------------

    def dress_window(self, window) -> None:
        """Give a window Bloom's icon and a title bar in the app's colour."""
        if sys.platform != "win32":
            return
        if ICON_FILE.exists():
            window.iconbitmap(str(ICON_FILE))
        window.after(260, lambda: self._colour_title_bar(window))

    def _colour_title_bar(self, window) -> None:
        """Match the Windows 11 title bar to the sidebar; do nothing elsewhere."""
        try:
            bar = theme.color("sidebar")[1:]
            text = theme.color("sidebar_text")[1:]
            handle = ctypes.windll.user32.GetParent(window.winfo_id())
            for attribute, colour in ((DWM_CAPTION_COLOR, bar), (DWM_TEXT_COLOR, text)):
                value = ctypes.c_int(int(colour[4:6] + colour[2:4] + colour[:2], 16))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    handle, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
        except (AttributeError, OSError, tk.TclError):
            pass

    def _set_appearance_mode(self, mode_string: str) -> None:
        """Follow light or dark mode, including when Windows changes it live."""
        super()._set_appearance_mode(mode_string)
        self.after(40, self._recolour_art)

    def _recolour_art(self) -> None:
        mode = ctk.get_appearance_mode()
        if mode == getattr(self, "_shown_mode", mode):
            return
        self._shown_mode = mode
        self._colour_title_bar(self)
        pending = [self]
        while pending:
            widget = pending.pop()
            if widget in self._doomed:
                continue  # on its way out: not worth redrawing
            pending.extend(widget.winfo_children())
            if isinstance(widget, widgets.ArtCanvas):
                widget.recolour()

    def destroy(self) -> None:
        """Close quietly: stop the speech helper and any waiting timers."""
        speech.shut_down()
        try:
            for job in self.tk.eval("after info").split():
                self.tk.call("after", "cancel", job)
        except tk.TclError:
            pass
        super().destroy()

    def _place_window(self) -> None:
        """Size the window to the screen (about 84%) and centre it."""
        scale = ctk.ScalingTracker.get_window_scaling(self)
        screen_w = self.winfo_screenwidth() / scale
        screen_h = self.winfo_screenheight() / scale
        width = int(min(max(screen_w * 0.84, 900), 1440, screen_w - 20))
        height = int(min(max(screen_h * 0.84, 580), 920, screen_h - 90))
        x = int((self.winfo_screenwidth() - width * scale) / 2)
        y = max(0, int((self.winfo_screenheight() - (height + 60) * scale) / 3))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.compact = width < theme.COMPACT_BELOW

    def start(self) -> None:
        """Load the accounts and show the login screen."""
        self.users, warning = storage.load_users(self.data_dir)
        self.apply_login_look()
        self._prepare_banner_art()
        self.show_login()
        effects.fade_in(self)
        if warning:
            self.after(400, lambda: widgets.toast(self, warning, "warning"))

    def _prepare_banner_art(self) -> None:
        """Draw the banners' 3D art on a background thread, so pages open sooner."""
        hue = theme.accent_hue
        specs = [
            (spec, hue)
            for page in PAGES.values()
            for spec in widgets.themed_specs(page.banner or [], hue)
        ]
        self._art_thread = threading.Thread(
            target=widgets.prepare_art,
            args=(specs, ctk.ScalingTracker.get_widget_scaling(self)),
            daemon=True,
        )
        self._art_thread.start()

    def apply_login_look(self) -> None:
        """Use the last user's font, colour and access needs on the login screens."""
        look = self.users["look"]
        self._set_text_size(look["text_size"])
        theme.set_font_choice(look["font"])
        theme.apply_look(look["accent"], look["high_contrast"])
        icons.reset_cache()
        self.configure(fg_color=theme.pair("bg"))
        self._colour_title_bar(self)

    # Screens before the main layout --------------------------------------------

    def _show_full(self, screen) -> None:
        """Show a screen that fills the window (login, onboarding)."""
        self._remove_shell()
        old = self.screen
        self.screen = screen
        screen.grid(row=0, column=0, columnspan=2, sticky="nsew")
        if old is not None:
            old.destroy()

    def restart_screen(self, screen) -> None:
        """Rebuild a login-side screen after its look changed."""
        if isinstance(screen, RegisterScreen):
            self.show_register()
        elif isinstance(screen, ResetScreen):
            self.show_reset()
        else:
            self.show_login()

    def show_login(self) -> None:
        """Show the login screen."""
        self._show_full(LoginScreen(self))

    def show_register(self) -> None:
        """Show the sign-up screen."""
        self._show_full(RegisterScreen(self))

    def show_reset(self) -> None:
        """Show the reset-password screen."""
        self._show_full(ResetScreen(self))

    def show_code(self, code: str, then, heading: str) -> None:
        """Show a recovery code once, then call `then()`."""
        self._show_full(CodeScreen(self, code, then, heading))

    # Session ----------------------------------------------------------------

    def log_in(self, user: dict) -> None:
        """Start a session; new users answer the setup questions first."""
        data, warning = storage.load_user_data(user["user_id"], self.data_dir)
        self.user = user
        self.user_data = data
        self.users["last_username"] = user["username"]
        self.save_users()
        if not profile.is_onboarded(data["profile"]):
            # A new account starts with what was chosen on the login screen.
            data["settings"].update(self.users["look"])
            if self._windows_animations_off():
                data["settings"]["reduce_motion"] = True
        self.apply_settings(rebuild=False)
        sfx.play("login")
        if profile.is_onboarded(data["profile"]):
            self.enter_main(data["settings"]["start_page"])
        else:
            self._show_full(Onboarding(self))
        if warning:
            self.after(400, lambda: widgets.toast(self, warning, "warning"))

    def enter_main(self, page: str = "home") -> None:
        """Show the sidebar layout and open a page."""
        if self.screen is not None:
            self.screen.destroy()
            self.screen = None
        self._remove_shell()
        self.sidebar = Sidebar(self, self.use_rail())
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.host = ctk.CTkFrame(self, fg_color=theme.pair("bg"), corner_radius=0)
        self.host.grid(row=0, column=1, sticky="nsew")
        self.page = None
        self.show_page(page)

    def confirm_log_out(self) -> None:
        """Ask, then log out."""
        if not self.user_data["settings"]["confirm_logout"] or widgets.confirm(
            self, "Log out?", "Your data stays saved on this computer.", "Log Out"
        ):
            self.log_out()

    def log_out(self) -> None:
        """End the session and return to the login screen."""
        sfx.play("logout")
        self._remove_shell()
        self.user = None
        self.user_data = None
        anim.reduce_motion = False
        ctk.set_appearance_mode("system")
        self.apply_login_look()
        self.show_login()

    def save_users(self) -> None:
        """Write all accounts to disk."""
        storage.save_users(self.users, self.data_dir)

    def save_user_data(self) -> None:
        """Write the logged-in user's data to disk; other pages will rebuild."""
        try:
            storage.save_user_data(self.user["user_id"], self.user_data, self.data_dir)
        except OSError:
            widgets.toast(
                self,
                "Couldn't save your data. Is the disk full or read-only?",
                "warning",
            )
        self.data_version += 1
        if self.sidebar is not None:
            self.sidebar.refresh_flower()
        self._check_full_bloom()

    def _check_full_bloom(self) -> None:
        """Celebrate the moment today's flower gets its last petal."""
        today = date.today()
        if garden.petal_count(self.user_data, today) < garden.TOTAL_PETALS:
            return
        if self.bloomed_on != today:
            self.bloomed_on = today
            self.after(500, lambda: effects.celebrate(self))

    def delete_user_files(self) -> None:
        """Delete the logged-in user's data file."""
        storage.delete_user_data(self.user["user_id"], self.data_dir)

    def apply_settings(self, rebuild: bool = True) -> None:
        """Apply every look, motion and sound setting; redraw the layout if asked."""
        settings = self.user_data["settings"]
        rebuild = rebuild and self.sidebar is not None
        if rebuild:
            # Take the old layout down first: restyling it would only redraw
            # widgets that are about to be replaced, which took seconds.
            self._remove_shell()
        anim.reduce_motion = settings["reduce_motion"]
        effects.configure(settings)
        sfx.configure(settings)
        widgets.configure(settings)
        theme.big_targets = settings["big_targets"]
        self._set_text_size(settings["text_size"])
        theme.set_font_choice(settings["font"], settings["bold_text"])
        theme.apply_look(
            self._accent_now(), settings["high_contrast"], settings["color_vision"]
        )
        icons.reset_cache()
        ctk.set_appearance_mode(settings["appearance"])
        self._shown_mode = ctk.get_appearance_mode()
        self.configure(fg_color=theme.pair("bg"))
        self._colour_title_bar(self)
        accent = settings["accent"]
        look = {
            "font": settings["font"],
            "accent": "bloom" if accent == theme.FOLLOW_CYCLE else accent,
            "text_size": settings["text_size"],
            "high_contrast": settings["high_contrast"],
        }
        if self.users["look"] != look:
            self.users["look"] = look
            self.save_users()
        today = date.today()
        if garden.petal_count(self.user_data, today) == garden.TOTAL_PETALS:
            self.bloomed_on = today  # already bloomed: nothing new to celebrate
        if rebuild:
            self.enter_main(self.current)

    def _set_text_size(self, size: str) -> None:
        """Scale text and controls; rescaling is slow, so only when it changes."""
        scale = TEXT_SIZES.get(size, 1.0)
        if scale != self.text_scale:
            self.text_scale = scale
            ctk.set_widget_scaling(scale)

    def _accent_now(self) -> str:
        """Return the accent to use: the chosen one, or today's cycle phase's."""
        accent = self.user_data["settings"]["accent"]
        if accent != theme.FOLLOW_CYCLE:
            return accent
        phase = insights.phase_today(self.user_data, date.today())
        return PHASE_ACCENTS.get(phase, "bloom")

    def use_rail(self) -> bool:
        """Return True when the sidebar should be the narrow icon rail."""
        chosen = self.user_data and self.user_data["settings"]["always_rail"]
        return self.compact or bool(chosen)

    @staticmethod
    def _windows_animations_off() -> bool:
        """Return True if Windows' "Animation effects" setting is off."""
        if sys.platform != "win32":
            return False
        try:
            enabled = ctypes.c_int(1)
            get_client_area_animation = 0x1042
            ctypes.windll.user32.SystemParametersInfoW(
                get_client_area_animation, 0, ctypes.byref(enabled), 0
            )
            return not enabled.value
        except (AttributeError, OSError):
            return False

    # Pages --------------------------------------------------------------------

    def show_page(self, name: str, animate: bool = True) -> None:
        """Open a sidebar page with a short slide-up transition.

        Built pages are kept, so going back to one is instant. A kept page is
        rebuilt only if data was saved since it was built, or the date changed.
        """
        if name not in PAGES:
            name = "home"
        if name in CYCLE_PAGES and not self.user_data["profile"]["track_cycle"]:
            name = "home"
        if self.host is None:
            return
        self._last_input = time.monotonic()
        page = self.pages.get(name)
        if page is not None and page is self._warm:
            self._warm = None  # opened now, so no longer prepared in the background
        self._hide_warm()
        stale = page is not None and (
            page.built_version != self.data_version or page.today != date.today()
        )
        if stale:
            if page is self.page:
                self.page = None  # so it is not hidden below after being destroyed
            page.destroy()
            page = None
        if page is None:
            page = PAGES[name](self, self.host)
            self.pages[name] = page
        old = self.page
        self.page = page
        self.current = name
        if old is not None and old is not page:
            old.place_forget()
        page.place(x=0, y=0, relwidth=1, relheight=1)
        page.lift()
        self.sidebar.select(name)
        if animate:
            effects.page_in(self, page)

    def _shortcut(self, number: int) -> None:
        """Ctrl+number opens the sidebar's nth page (hidden pages are skipped)."""
        if self.sidebar is None:
            return
        tracking = self.user_data["profile"]["track_cycle"]
        visible = [key for key in ORDER if tracking or key not in CYCLE_PAGES]
        if number <= len(visible):
            self.show_page(visible[number - 1])

    def _remove_shell(self) -> None:
        """Take down the sidebar and pages.

        Everything is hidden at once (Windows destroys hidden widgets about three
        times faster). The kept pages are slow to destroy, so they go later, one
        per quiet moment (see _warm_tick), and a new look appears seconds sooner.
        """
        sidebar, host = self.sidebar, self.host
        for widget in (sidebar, host):
            if widget is not None:
                widget.grid_remove()
        if sidebar is not None:
            sidebar.destroy()
        if host is not None:
            for page in {self.page, self._warm} - {None}:
                page.destroy()  # these two may still be building: stop them now
            later = [*host.winfo_children(), host]
            widgets.forget_styles(later)
            self._doomed.extend(later)
            # Many quick changes in a row must not pile up old pages (Windows
            # limits how many controls and menus one program may have).
            while len(self._doomed) > MAX_WAITING_PAGES:
                try:
                    self._doomed.pop(0).destroy()
                except tk.TclError:
                    pass
        self.sidebar = self.host = self.page = self._warm = None
        self.pages = {}

    # Preparing pages while the user is idle ----------------------------------------

    def note_input(self, _event=None) -> None:
        """Remember that the user is busy, and hide a page being prepared."""
        self._last_input = time.monotonic()
        widgets.hold_hidden_builds = True
        self._hide_warm()

    def _hide_warm(self) -> None:
        warm = self._warm
        if warm is not None and warm is not self.page:
            try:
                warm.place_forget()
            except tk.TclError:
                self._warm = None

    def _warm_tick(self) -> None:
        """Build the other pages in quiet moments, so they open instantly.

        A page takes a second or two to build, and every save makes the kept
        pages out of date. So when nobody has clicked or typed for a moment,
        Bloom builds the next page that is missing or out of date, hidden under
        the page being read, one page at a time. Any click or key pauses it.
        """
        self.after(WARM_CHECK_MS, self._warm_tick)
        now = time.monotonic()
        late = now - self._last_tick - WARM_CHECK_MS / 1000
        self._last_tick = now
        warm = self._warm
        drawing_warm = (
            warm is not None and warm.winfo_exists() and warm.winfo_ismapped()
        )
        if late > 0.25 and not drawing_warm:
            self._last_input = now  # the window was busy (drawing a save, say)
        dialog_open = any(isinstance(w, tk.Toplevel) for w in self.winfo_children())
        quiet = now - self._last_input >= WARM_IDLE_S and not anim.busy()
        quiet = quiet and not dialog_open  # never slow down typing in a dialog
        # Cards of hidden pages also wait while the user is busy.
        widgets.hold_hidden_builds = not quiet
        if not quiet:
            return
        if self._doomed:
            try:
                self._doomed.pop(0).destroy()  # one old hidden page per quiet moment
            except tk.TclError:
                pass
            return
        if self.sidebar is None or self.page is None or self.user_data is None:
            return
        if self._art_thread.is_alive() or widgets.still_building(self.page):
            return
        if warm is not None:
            try:
                if not warm.winfo_exists():
                    raise tk.TclError
                if not warm.winfo_ismapped():
                    self._place_under(warm)  # resume: let it lay out and draw
                    return
                if widgets.still_building(warm) and now - self._warm_since < 30:
                    return  # (after 30 s, give up rather than wait forever)
                if warm is not self.page:
                    warm.place_forget()  # ready: hidden until it is opened
            except tk.TclError:
                pass
            self._warm = None
            return
        name = self._next_to_warm()
        if name is None:
            return
        old = self.pages.pop(name, None)
        if old is not None:
            old.destroy()
        self.warming = True
        try:
            page = PAGES[name](self, self.host)
        finally:
            self.warming = False
        self.pages[name] = page
        self._warm = page
        self._warm_since = now
        self._place_under(page)

    @staticmethod
    def _place_under(page) -> None:
        """Lay a page out at full size, under the page being shown."""
        page.place(x=0, y=0, relwidth=1, relheight=1)
        page.lower()

    def _next_to_warm(self) -> str | None:
        """Return the page to prepare next; the ones after this page come first."""
        tracking = self.user_data["profile"]["track_cycle"]
        names = [key for key in ORDER if tracking or key not in CYCLE_PAGES]
        if self.current in names:
            after = names.index(self.current) + 1
            names = names[after:] + names[:after]
        for name in names:
            page = self.pages.get(name)
            if name == self.current or page is self.page:
                continue
            if (
                page is None
                or page.built_version != self.data_version
                or page.today != date.today()
            ):
                return name
        return None

    # Adapting to the window size -----------------------------------------------

    def _on_resize(self, event) -> None:
        if event.widget is not self:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(140, self._check_layout)

    # Keyboard and reading aloud ----------------------------------------------------

    def _click_away(self, event) -> None:
        """Clicking outside a text box takes the cursor out of it."""
        widget = event.widget
        while widget is not None and widget is not self:
            if isinstance(widget, (widgets.Field, ctk.CTkTextbox, ctk.CTkEntry)):
                return
            widget = getattr(widget, "master", None)
        if widget is self:
            try:
                self.focus_set()
            except tk.TclError:
                pass

    def open_quick_find(self) -> None:
        """Open the search box that reaches any page, setting or action."""
        if self.user_data is not None and self.sidebar is not None:
            palette.CommandPalette(self, self.commands())

    def commands(self) -> list[tuple]:
        """Return everything Quick Find can reach: (title, words, icon, action)."""
        tracking = self.user_data["profile"]["track_cycle"]
        found = []
        for _, entries in NAV:
            for key, text, icon_name, _ in entries:
                if tracking or key not in CYCLE_PAGES:
                    action = lambda k=key: self.show_page(k)  # noqa: E731
                    found.append((text, "page open go", icon_name, action))
        settings = self.user_data["settings"]
        mode_word = "light" if ctk.get_appearance_mode() == "Dark" else "dark"
        found += [
            ("Add a glass of water", "drink log nutrition", "cup", self.add_glass),
            ("Log a period", "cycle start menstruation", "drop", lambda: self.show_page("cycle")),
            ("Log my mood", "journal feeling symptoms", "smile", lambda: self.show_page("journal")),
            ("Log my weight", "bmi scale", "scale", lambda: self.show_page("bmi")),
            ("Log blood pressure", "vitals heart", "heart", lambda: self.show_page("vitals")),
            ("Take a breath", "breathing calm stress garden", "heart", lambda: self.show_page("garden")),
            (f"Switch to {mode_word} mode", "appearance theme night", "sun", self.toggle_mode),
            (
                f"Turn high contrast {'off' if settings['high_contrast'] else 'on'}",
                "accessibility vision",
                "eye_access",
                self.toggle_contrast,
            ),
            ("Read this page aloud", "accessibility speech screen reader F2", "speaker", self.read_page),
            ("Keyboard shortcuts", "help keys F1", "keyboard", self.show_help),
            ("Full screen", "presentation F11", "fullscreen", self.toggle_full_screen),
            ("Log out", "sign out exit", "logout", self.confirm_log_out),
        ]  # fmt: skip
        tabs = (
            ("Profile", "user", "name height birth cycle"),
            ("Goals", "flame", "steps water sleep"),
            ("Appearance", "palette", "theme colour font effects transition"),
            ("Accessibility", "eye_access", "text size contrast colour blind dyslexia motion keyboard read aloud"),
            ("Sound", "speaker", "volume music effects mute"),
            ("Preferences", "gear", "units kg lb start page"),
            ("Account", "lock", "password export delete recovery doctor summary"),
            ("About", "info", "version sources"),
        )  # fmt: skip
        for tab, icon_name, words in tabs:
            action = lambda t=tab: self.open_settings(t)  # noqa: E731
            found.append((f"Settings: {tab}", words, icon_name, action))
        return found

    def open_settings(self, tab: str) -> None:
        """Open Settings on a tab."""
        self.settings_tab = tab
        self.pages.pop("settings", None)
        self.show_page("settings")

    def add_glass(self) -> None:
        """Log a glass of water from anywhere."""
        goal = self.user_data["goals"]["water_ml"]
        total = daylog.add_amount(self.user_data, date.today(), "water_ml", 250)
        self.save_user_data()
        widgets.toast(self, f"+250 ml water: {int(total):,} of {goal:,} ml today")
        if total >= goal > total - 250:
            effects.celebrate(self)
        self.show_page(self.current, animate=False)

    def toggle_mode(self) -> None:
        """Switch between light and dark mode."""
        dark = ctk.get_appearance_mode() == "Dark"
        self.user_data["settings"]["appearance"] = "light" if dark else "dark"
        self.save_user_data()
        self.apply_settings(rebuild=True)

    def toggle_contrast(self) -> None:
        """Turn high contrast on or off."""
        settings = self.user_data["settings"]
        settings["high_contrast"] = not settings["high_contrast"]
        self.save_user_data()
        self.apply_settings(rebuild=True)

    def show_help(self) -> None:
        """Show the keyboard shortcuts."""
        palette.show_shortcuts(self)

    def read_page(self) -> None:
        """Read what is on screen aloud."""
        if not speech.available():
            widgets.toast(
                self, "Reading aloud isn't available on this computer", "info"
            )
            return
        if self.page is not None:
            speech.speak(self.page.spoken())
        elif self.screen is not None:
            speech.speak(". ".join(widgets.spoken_text(self.screen)))

    def jump_focus(self) -> None:
        """Move the keyboard between the sidebar and the page."""
        if self.sidebar is None or self.page is None:
            return
        focused = self.focus_get()
        in_sidebar = focused is not None and str(focused).startswith(str(self.sidebar))
        start = self.page.column if in_sidebar else self.sidebar
        target = start.tk_focusNext()
        if target is not None:
            target.focus_set()

    def toggle_full_screen(self) -> None:
        """Full screen on or off; handy when presenting."""
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

    def _escape(self) -> None:
        speech.stop()
        if self.attributes("-fullscreen"):
            self.attributes("-fullscreen", False)

    def change_text_size(self, step: int) -> None:
        """Make all text and controls a step bigger or smaller."""
        if self.user_data is None:
            return
        settings = self.user_data["settings"]
        index = TEXT_SIZE_ORDER.index(settings["text_size"]) + step
        if 0 <= index < len(TEXT_SIZE_ORDER):
            settings["text_size"] = TEXT_SIZE_ORDER[index]
            self.save_user_data()
            self.apply_settings(rebuild=True)

    def _check_layout(self) -> None:
        self._resize_job = None
        # Bigger text needs more room, so the rail arrives sooner.
        width = self.winfo_width() / ctk.ScalingTracker.get_widget_scaling(self)
        compact = width < theme.COMPACT_BELOW
        if compact == self.compact:
            return
        self.compact = compact
        if self.sidebar is not None:
            self.sidebar.destroy()
            self.sidebar = Sidebar(self, self.use_rail())
            self.sidebar.grid(row=0, column=0, sticky="ns")
            self.sidebar.select(self.current)
        elif self.screen is not None and hasattr(self.screen, "adapt"):
            self.screen.adapt(compact)

    # Errors -------------------------------------------------------------------

    def report_callback_exception(
        self, exc: type[BaseException], val: BaseException, tb: TracebackType | None
    ) -> None:
        """Show an unexpected error from a click in a dialog, not only the console."""
        traceback.print_exception(exc, val, tb)
        messagebox.showerror(
            "Something went wrong", f"{exc.__name__}: {val}", parent=self
        )
