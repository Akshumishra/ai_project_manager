from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from meeting_bot.config import BotConfig

logger = logging.getLogger(__name__)

# ── Selectors ──────────────────────────────────────────────────────────────────
# These use attribute/text-based locators so they are resilient to class changes.
_SEL_JOIN_NOW = "button[jsname='Qx7uuf'], button[data-idom-class*='join']"
_SEL_ASK_JOIN = "button[jsname='NQs5Ob']"  # "Ask to join" in lobby
_SEL_LEAVE_BTN = "[data-tooltip*='Leave'], [aria-label*='Leave call']"
_SEL_MIC_OFF = "[data-is-muted='true'][data-tooltip*='microphone']"
_SEL_LEFT_SCREEN = (
    '//h1[contains(text(), "left the meeting") or contains(text(), "You\'ve left")]'
)

_GOOGLE_SIGN_IN_URL = "https://accounts.google.com/ServiceLogin"
_MEET_BASE = "https://meet.google.com"

# How long (seconds) to wait between polls when watching for meeting end.
_POLL_INTERVAL = 10


class MeetBot:
    """
    Playwright-based Google Meet participant bot.

    The bot reuses a persistent Chromium browser profile so that Google
    authentication cookies survive across separate runs. On the very first
    run you must call :py:meth:`seed_login` (or run the CLI ``seed-login``
    command) to authenticate interactively; afterwards the profile is reused
    automatically.
    """

    def __init__(self, config: BotConfig, user_data_dir: Path | None = None) -> None:
        self._config = config
        self._user_data_dir = user_data_dir or config.browser_profile_dir
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def setup(self, headless: bool | None = None) -> None:
        """Start Playwright and open a persistent browser context."""
        self._playwright = await async_playwright().start()

        is_headless = headless if headless is not None else self._config.headless

        profile_dir = str(self._user_data_dir)
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        logger.info(
            "Launching Chromium (headless=%s) with profile: %s",
            is_headless,
            profile_dir,
        )

        # launch_persistent_context keeps cookies/localStorage between runs.
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=is_headless,
            args=[
                "--use-fake-device-for-media-stream",  # Don't require physical mic/cam.
                "--use-fake-ui-for-media-stream",  # Auto-grant mic/cam permission prompts.
                "--autoplay-policy=no-user-gesture-required",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",  # Reduce bot fingerprint.
                "--window-size=1920,1080",
                "--lang=en-US,en;q=0.9",
            ],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            permissions=["camera", "microphone"],
            ignore_https_errors=True,
        )
        logger.info("Browser context ready.")

    async def seed_login(self) -> None:
        """
        Open a browser window for interactive Gmail login.

        The user logs in manually; cookies are persisted to the profile.
        Only needs to be run once (or when cookies expire).
        """
        if self._context is None:
            raise RuntimeError("Call setup() before seed_login().")

        page = await self._context.new_page()
        logger.info("Opening Gmail sign-in page for interactive login…")
        await page.goto(_GOOGLE_SIGN_IN_URL)

        print("\n" + "=" * 60)
        print("  Please sign in to your Google account in the browser.")
        print("  Once signed in, CLOSE the browser tab/window to continue.")
        print("=" * 60 + "\n")

        # Wait until the user closes the page (navigates away or closes it).
        try:
            await page.wait_for_url("**myaccount.google.com**", timeout=300_000)
        except Exception:
            pass  # User may close directly or end up on a different URL.

        await page.close()
        logger.info(
            "Login complete — profile saved to: %s", self._config.browser_profile_dir
        )

    async def join_meeting(self, meet_url: str) -> None:
        """
        Navigate to *meet_url* and click 'Join now'.

        Handles:
        - Camera / microphone pre-join dialogs (turns mic + cam off).
        - 'Ask to join' lobby button when the user is not the host.
        """
        if self._context is None:
            raise RuntimeError("Call setup() before join_meeting().")

        self._page = await self._context.new_page()
        logger.info("Navigating to Meet URL: %s", meet_url)
        await self._page.goto(meet_url, wait_until="domcontentloaded")

        # Allow Google Meet's React app to initialise.
        await self._page.wait_for_timeout(3_000)

        # ── Dismiss pre-join mic/cam checks ───────────────────────────────────
        await self._mute_mic_and_camera()

        # ── Click 'Join now' or 'Ask to join' ─────────────────────────────────
        joined = False
        # Add a few more common selectors for the Join button
        common_selectors = [
            _SEL_JOIN_NOW,
            _SEL_ASK_JOIN,
            "button:has-text('Join now')",
            "button:has-text('Ask to join')",
            "button:has-text('Join')",
            "[aria-label*='Join now']",
            "role=button[name*='Join now']",
        ]

        for attempt in range(1, 5):
            logger.debug("Join attempt %d…", attempt)
            for selector in common_selectors:
                try:
                    btn = self._page.locator(selector).first
                    if await btn.is_visible(timeout=2_000):
                        await btn.click()
                        joined = True
                        logger.info("Clicked button via selector: %s", selector)
                        break
                except Exception:
                    continue
            if joined:
                break
            await self._page.wait_for_timeout(3_000)

        if not joined:
            # DEBUG: Log all visible buttons to see what the bot is looking at
            try:
                buttons = await self._page.locator("button").all_inner_texts()
                logger.error(
                    "Could not find Join button. Visible buttons on page: %s", buttons
                )
                await self._page.screenshot(path="join_failure.png")
            except Exception as e:
                logger.error("Failed to collect debug info: %s", e)

            raise RuntimeError(
                "Could not find Join / Ask-to-join button after 4 attempts. "
                "Check if the Meet URL is valid and the account has access."
            )

        # Give Meet a few seconds to fully enter the call.
        await self._page.wait_for_timeout(5_000)
        logger.info("Successfully joined the meeting.")

    async def wait_for_meeting_end(self, max_seconds: int) -> None:
        """
        Block until the meeting ends or *max_seconds* has elapsed.

        Polls every ``_POLL_INTERVAL`` seconds and checks for the
        'You've left the meeting' heading (shown after everyone leaves
        or the bot is removed).
        """
        if self._page is None:
            raise RuntimeError("Call join_meeting() first.")

        logger.info("Waiting for meeting to end (max %ds)…", max_seconds)
        elapsed = 0

        while elapsed < max_seconds:
            try:
                left_indicator = self._page.locator(_SEL_LEFT_SCREEN).first
                if await left_indicator.is_visible(timeout=1_000):
                    logger.info("Meeting ended — 'left the meeting' screen detected.")
                    return
            except Exception:
                pass

            # Also check if the page URL changed to the post-call survey/lobby.
            current_url = self._page.url
            if "meet.google.com" not in current_url or "/lookup/" in current_url:
                logger.info(
                    "Meeting appears to have ended (URL changed to: %s).", current_url
                )
                return

            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL
            logger.debug("Still in meeting… (%ds elapsed)", elapsed)

        logger.warning("Max meeting duration (%ds) reached — leaving now.", max_seconds)

    async def leave_meeting(self) -> None:
        """Click the 'Leave call' button if still in the meeting."""
        if self._page is None:
            return

        try:
            leave_btn = self._page.locator(_SEL_LEAVE_BTN).first
            if await leave_btn.is_visible(timeout=3_000):
                await leave_btn.click()
                logger.info("Clicked 'Leave call'.")
                await self._page.wait_for_timeout(2_000)
        except Exception as exc:
            logger.debug("Could not find or click Leave button: %s", exc)

    async def teardown(self) -> None:
        """Close the browser and stop Playwright."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        logger.info("Browser closed.")

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _mute_mic_and_camera(self) -> None:
        """
        Attempt to turn off the microphone and camera before joining.
        Uses both selector-based clicks and keyboard shortcuts as fallbacks.
        """
        if self._page is None:
            return

        # Keyboard shortcuts: Ctrl+D (mic), Ctrl+E (camera)
        for shortcut, label in [("d", "microphone"), ("e", "camera")]:
            try:
                await self._page.keyboard.press(f"Control+{shortcut}")
                logger.debug("Toggled %s via keyboard.", label)
            except Exception:
                pass

        await self._page.wait_for_timeout(500)
