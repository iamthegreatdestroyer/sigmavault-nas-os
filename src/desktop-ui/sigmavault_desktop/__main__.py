"""Entry point for SigmaVault Native UI application."""

import sys
import logging


def main() -> int:
    """Main entry point for the application."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Import here to avoid import errors early
        from sigmavault_desktop.app import Application

        logger.info("Starting SigmaVault Native UI...")
        app = Application()
        return app.run(sys.argv)

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Please ensure GTK4 and libadwaita are installed:")
        logger.error("  apt install python3-gi gir1.2-gtk-4.0 gir1.2-adwaita-1")
        return 1
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
