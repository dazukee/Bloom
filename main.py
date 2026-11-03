"""Entry point: run `python main.py` to start the app."""

from tracker.ui.app import App


def main() -> None:
    """Open the main window and run until it is closed."""
    App().mainloop()


if __name__ == "__main__":
    main()
