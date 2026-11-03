"""Open Bloom with a made-up demo account; your real data is never touched.

    python -m tracker.ui.preview             the Today page
    python -m tracker.ui.preview cycle       any page: home, cycle, bbt, journal,
                                             vitals, activity, nutrition, bmi, settings
    python -m tracker.ui.preview login       the login screen (demo / bloom2026)

The demo lives in a temporary folder that is deleted when the window closes,
so it is safe for presentations: log, click and change anything.
"""

import sys
import tempfile
from datetime import date
from pathlib import Path

from tracker import auth, demo, storage
from tracker.ui.app import PAGES, App


def make_demo_folder(folder: Path) -> None:
    """Create the demo account and its 90 days of data in `folder`."""
    users = storage.new_users()
    user, _ = auth.register_user(
        users, demo.DEMO_USERNAME, demo.DEMO_PASSWORD, demo.DEMO_PASSWORD, date.today()
    )
    users["last_username"] = demo.DEMO_USERNAME
    storage.save_users(users, folder)
    storage.save_user_data(user["user_id"], demo.make_demo_data(date.today()), folder)


class PreviewApp(App):
    """The real app, pointed at the temporary demo folder."""

    def __init__(self, folder: Path, page: str) -> None:
        self.start_page = page
        super().__init__(data_dir=folder)

    def start(self) -> None:
        """Log straight in to the demo account (unless the login page was asked for)."""
        super().start()
        self.title("Bloom (demo account: nothing is saved to your real data)")
        if self.start_page != "login":
            user = self.users["users"][0]
            self.log_in(user)
            self.show_page(self.start_page, animate=False)


def main() -> None:
    """Open the page named on the command line."""
    page = sys.argv[1] if len(sys.argv) > 1 else "home"
    if page not in PAGES and page != "login":
        sys.exit(
            f"Unknown page {page!r}. Choose one of: {', '.join([*PAGES, 'login'])}"
        )
    with tempfile.TemporaryDirectory(prefix="bloom-demo-") as folder:
        make_demo_folder(Path(folder))
        PreviewApp(Path(folder), page).mainloop()


if __name__ == "__main__":
    main()
