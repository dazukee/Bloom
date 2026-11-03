"""The main window: login, onboarding, the adaptive sidebar and page transitions.

What a screen may use (the contract between app.py and every page):
    app.users, app.user, app.user_data       accounts, the session, its data
    app.save_users(), app.save_user_data()   write them to disk
    app.delete_user_files()                  remove the user's data file
    app.log_in(user), app.log_out()          start or end a session
    app.show_login(), show_register(), show_reset(), show_code(...)
    app.show_page(name)                      open a sidebar page (keys of PAGES)
    app.enter_main(page)                     show the sidebar layout
    app.apply_settings(rebuild=True)         re-apply appearance and motion
"""

import traceback
from datetime import date
from tkinter import messagebox
from types import TracebackType

import customtkinter as ctk

from tracker import profile, storage
from tracker.ui import anim, icons, render3d, theme, widgets
from tracker.ui.activity_page import ActivityPage
from tracker.ui.auth_pages import CodeScreen, LoginScreen, RegisterScreen, ResetScreen
from tracker.ui.bbt_page import BbtPage
from tracker.ui.bmi_page import BmiPage
from tracker.ui.cycle_page import CyclePage
from tracker.ui.home_page import HomePage
from tracker.ui.journal_page import JournalPage
from tracker.ui.nutrition_page import NutritionPage
from tracker.ui.onboarding import Onboarding
from tracker.ui.settings_page import SettingsPage
from tracker.ui.vitals_page import VitalsPage

# Sidebar groups: (group label, [(page key, label, icon, page class), ...])
NAV = [
    ("", [("home", "Today", "home", HomePage)]),
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


def _shorten(text: str, limit: int) -> str:
    """Fit a name in the sidebar: first word if too long, then cut with an ellipsis."""
    if len(text) > limit and " " in text:
        text = text.split()[0]
    return text if len(text) <= limit else text[: limit - 1] + "…"


class Sidebar(ctk.CTkFrame):
    """Labelled navigation (or an icon rail on narrow windows) with the account."""

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
        track_cycle = app.user_data["profile"]["track_cycle"]

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=14, pady=(20, 14))
        # A light pearl sphere, so the logo stands out on the purple panel.
        sphere = render3d.sphere(64, (167, 139, 250), render3d.PEARL)
        logo = ctk.CTkImage(sphere, size=(30, 30))
        ctk.CTkLabel(brand, text="", image=logo).grid(row=0, column=0, rowspan=2)
        if not compact:
            widgets.label(brand, theme.APP_NAME, "title3", "sidebar_text").grid(
                row=0, column=1, sticky="w", padx=(10, 0)
            )
            widgets.label(brand, theme.APP_TAGLINE, "caption", "sidebar_muted").grid(
                row=1, column=1, sticky="w", padx=(10, 0)
            )

        row = 1
        for group, entries in NAV:
            if group and not compact:
                widgets.label(self, group, "footnote", "sidebar_muted").grid(
                    row=row, column=0, sticky="w", padx=22, pady=(14, 4)
                )
                row += 1
            elif group:
                ctk.CTkFrame(self, height=1, fg_color=theme.pair("sidebar_hover")).grid(
                    row=row, column=0, sticky="ew", padx=18, pady=10
                )
                row += 1
            for key, text, icon_name, _ in entries:
                if key in CYCLE_PAGES and not track_cycle:
                    continue
                self._item(row, key, text, icon_name)
                row += 1
        self.rowconfigure(row, weight=1)
        row += 1
        self._item(row, *SETTINGS_ITEM[:3])
        row += 1
        self._account(row)

        self.marker = ctk.CTkFrame(
            self,
            width=4,
            height=22,
            corner_radius=2,
            fg_color=theme.pair("sidebar_marker"),
        )
        self.marker_y = None

    def _item(self, row: int, key: str, text: str, icon_name: str) -> None:
        item = ctk.CTkButton(
            self,
            text="" if self.compact else text,
            image=icons.icon(icon_name, 20, "sidebar_muted"),
            compound="left",
            anchor="center" if self.compact else "w",
            height=42,
            corner_radius=10,
            font=theme.font("body"),
            fg_color="transparent",
            hover_color=theme.pair("sidebar_hover"),
            text_color=theme.pair("sidebar_text"),
            command=lambda k=key: self.app.show_page(k),
        )
        item.grid(row=row, column=0, sticky="ew", padx=12, pady=1)
        item.icon_name = icon_name
        if self.compact:
            widgets.Tooltip(item, text)
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
            padx=12,
            pady=(8, 16),
        )
        box.columnconfigure(1, weight=1)
        # A true circle: a round frame with the initials centred on it (a
        # CTkLabel alone would stretch into a pill around its text).
        avatar = ctk.CTkFrame(
            box,
            width=36,
            height=36,
            corner_radius=18,
            fg_color=theme.pair("sidebar_text"),
        )
        avatar.grid(row=0, column=0, rowspan=2, padx=8, pady=8)
        ctk.CTkLabel(
            avatar,
            text=profile.initials(name),
            font=theme.font("label"),
            text_color=theme.pair("sidebar"),
            width=1,
            height=1,
        ).place(relx=0.5, rely=0.5, anchor="center")
        widgets.Tooltip(avatar, f"{name} (@{self.app.user['username']})")
        if not self.compact:
            widgets.label(box, _shorten(name, 13), "headline", "sidebar_text").grid(
                row=0, column=1, sticky="sw"
            )
            widgets.label(
                box,
                _shorten(f"@{self.app.user['username']}", 18),
                "caption",
                "sidebar_muted",
            ).grid(row=1, column=1, sticky="nw")
            logout = ctk.CTkButton(
                box,
                text="",
                image=icons.icon("logout", 18, "sidebar_text"),
                width=32,
                height=32,
                corner_radius=theme.RADIUS_CONTROL,
                fg_color="transparent",
                hover_color=theme.pair("sidebar"),
                command=self.app.confirm_log_out,
            )
            logout.grid(row=0, column=2, rowspan=2, padx=(0, 6))
            widgets.Tooltip(logout, "Log out")

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
        except Exception:
            return
        start = self.marker_y if self.marker_y is not None else target
        self.marker_y = target

        def step(t: float) -> None:
            self.marker.place(x=2, y=anim.lerp(start, target, t))

        anim.animate(
            self.marker, theme.BASE + 60, step, ease=anim.spring, key="nav-marker"
        )


class App(ctk.CTk):
    """The main window; one instance runs for the whole program."""

    def __init__(self, data_dir=storage.DATA_DIR) -> None:
        super().__init__()
        theme.reset_fonts()
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
        self.current = "home"
        self.compact = False
        self._resize_job = None
        self.bind("<Configure>", self._on_resize)
        for number in range(1, 10):
            self.bind(f"<Control-Key-{number}>", lambda _e, n=number: self._shortcut(n))
        self.start()

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
        self.show_login()
        if warning:
            self.after(400, lambda: widgets.toast(self, warning, "warning"))

    # Screens before the main layout --------------------------------------------

    def _show_full(self, screen) -> None:
        """Show a screen that fills the window (login, onboarding)."""
        self._remove_shell()
        old = self.screen
        self.screen = screen
        screen.grid(row=0, column=0, columnspan=2, sticky="nsew")
        if old is not None:
            old.destroy()

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
        self.apply_settings(rebuild=False)
        if profile.is_onboarded(data["profile"]):
            self.enter_main("home")
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
        self.sidebar = Sidebar(self, self.compact)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.host = ctk.CTkFrame(self, fg_color=theme.pair("bg"), corner_radius=0)
        self.host.grid(row=0, column=1, sticky="nsew")
        self.page = None
        self.show_page(page)

    def confirm_log_out(self) -> None:
        """Ask, then log out."""
        if widgets.confirm(
            self, "Log out?", "Your data stays saved on this computer.", "Log Out"
        ):
            self.log_out()

    def log_out(self) -> None:
        """End the session and return to the login screen."""
        self.user = None
        self.user_data = None
        anim.reduce_motion = False
        ctk.set_appearance_mode("system")
        self.show_login()

    def save_users(self) -> None:
        """Write all accounts to disk."""
        storage.save_users(self.users, self.data_dir)

    def save_user_data(self) -> None:
        """Write the logged-in user's data to disk; other pages will rebuild."""
        storage.save_user_data(self.user["user_id"], self.user_data, self.data_dir)
        self.data_version += 1

    def delete_user_files(self) -> None:
        """Delete the logged-in user's data file."""
        storage.delete_user_data(self.user["user_id"], self.data_dir)

    def apply_settings(self, rebuild: bool = True) -> None:
        """Apply appearance and motion settings; redraw the layout if asked."""
        settings = self.user_data["settings"]
        anim.reduce_motion = settings["reduce_motion"]
        ctk.set_appearance_mode(settings["appearance"])
        if rebuild and self.sidebar is not None:
            self.enter_main(self.current)

    # Pages --------------------------------------------------------------------

    def show_page(self, name: str, animate: bool = True) -> None:
        """Open a sidebar page with a short slide-up transition.

        Built pages are kept, so going back to one is instant. A kept page is
        rebuilt only if data was saved since it was built, or the date changed.
        """
        if name in CYCLE_PAGES and not self.user_data["profile"]["track_cycle"]:
            name = "home"
        if self.host is None:
            return
        page = self.pages.get(name)
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
            anim.animate(
                page,
                theme.PAGE_IN,
                lambda t: page.place_configure(y=26 * (1 - t)),
                ease=anim.ease_out_cubic,
                key="page",
            )

    def _shortcut(self, number: int) -> None:
        """Ctrl+number opens the sidebar's nth page (hidden pages are skipped)."""
        if self.sidebar is None:
            return
        tracking = self.user_data["profile"]["track_cycle"]
        visible = [key for key in ORDER if tracking or key not in CYCLE_PAGES]
        if number <= len(visible):
            self.show_page(visible[number - 1])

    def _remove_shell(self) -> None:
        for name in ("sidebar", "host"):
            widget = getattr(self, name)
            if widget is not None:
                widget.destroy()
                setattr(self, name, None)
        self.page = None
        self.pages = {}

    # Adapting to the window size -----------------------------------------------

    def _on_resize(self, event) -> None:
        if event.widget is not self:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(140, self._check_layout)

    def _check_layout(self) -> None:
        self._resize_job = None
        width = self.winfo_width() / ctk.ScalingTracker.get_window_scaling(self)
        compact = width < theme.COMPACT_BELOW
        if compact == self.compact:
            return
        self.compact = compact
        if self.sidebar is not None:
            self.sidebar.destroy()
            self.sidebar = Sidebar(self, compact)
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
