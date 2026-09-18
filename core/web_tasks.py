"""Conservative automation for the ordinary douyin.com web chat UI.

The default mode is a non-sending smoke test. A send is attempted at most once
per target; a visible outgoing bubble is not treated as recipient delivery.
"""

import re
import time
from urllib.parse import quote, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Error as PlaywrightError

from core.browser import get_browser
from core.msg_builder import build_message
from utils.config import get_config, get_userData
from utils.logger import setup_logger

BASE_URL = "https://www.douyin.com"
config = get_config()
logger = setup_logger(level=config.get("logLevel", "Info"))


def exact_id_pattern(value):
    return re.compile(r"抖音号\s*[:：]\s*" + re.escape(str(value)) + r"(?!\d)")


def find_target_link(page, target, match_mode):
    page.goto(f"{BASE_URL}/search/{quote(str(target), safe='')}?type=user")
    links = page.locator('a[href*="/user/"]')
    if match_mode == "short_id" or str(target).isdigit():
        matches = links.filter(has_text=exact_id_pattern(target))
    elif match_mode == "nickname":
        pattern = re.compile(r"^\s*" + re.escape(str(target)) + r"(?:\s|$)")
        matches = links.filter(has_text=pattern)
    else:
        raise ValueError(f"Unsupported MATCH_MODE: {match_mode}")
    matches.first.wait_for(timeout=config["browserTimeout"])
    if matches.count() != 1:
        raise RuntimeError(f"Target {target!r} is ambiguous ({matches.count()} matches)")
    return matches.first


def verify_owner(page, username, unique_id):
    page.goto(f"{BASE_URL}/user/self", wait_until="domcontentloaded")
    # The nickname heading can change with Douyin page revisions. The exact
    # Douyin ID is the stable account identity when one is configured.
    identity = (
        page.get_by_text(exact_id_pattern(unique_id))
        if str(unique_id).isdigit()
        else page.get_by_role("heading", name=username, exact=True)
    )
    try:
        identity.wait_for(timeout=min(config["browserTimeout"], 35000))
    except PlaywrightTimeoutError as exc:
        if (page.get_by_role("heading", name="未登录", exact=True).is_visible()
                or page.get_by_role("button", name="登录", exact=True).is_visible()):
            raise RuntimeError(
                "Douyin sender is not logged in on the GitHub runner; "
                "refresh the COOKIES_<UNIQUE_ID> environment secret"
            ) from exc
        raise RuntimeError(
            "Douyin sender identity could not be verified; "
            "the page may have changed or failed to load. No message was sent"
        ) from exc

def target_spec(target):
    if not isinstance(target, dict):
        return str(target), None
    unique_id = str(target.get("unique_id", ""))
    parsed = urlparse(str(target.get("profile_url", "")))
    if (not unique_id.isdigit() or parsed.scheme != "https"
            or parsed.netloc != "www.douyin.com"
            or not re.fullmatch(r"/user/[A-Za-z0-9_-]+", parsed.path)):
        raise ValueError("Target must have a numeric unique_id and a douyin.com profile_url")
    return unique_id, f"{BASE_URL}{parsed.path}"


class ChatInputUnavailable(RuntimeError):
    pass


def ensure_messaging_login(page, submitted=False):
    if page.locator('[id^="login-full-panel"]').is_visible():
        stage = "after attempted submission" if submitted else "before submission"
        raise RuntimeError(
            f"Douyin messaging requested a fresh login {stage}; "
            "the runner's Cookie session is insufficient for reliable sending. "
            "Do not auto-retry"
        )


def open_fresh_chat(context, profile_url, target_id, match_mode, submitted=False):
    """Reopen a chat to require a durable IM session before composing."""
    for page in list(context.pages):
        if not page.is_closed():
            page.close()
    fresh = context.new_page()
    fresh.goto(profile_url, wait_until="domcontentloaded")
    if match_mode == "short_id" or target_id.isdigit():
        fresh.get_by_text(exact_id_pattern(target_id)).wait_for(
            timeout=config["browserTimeout"]
        )
    ensure_messaging_login(fresh, submitted=submitted)
    try:
        fresh.get_by_role("button", name="私信", exact=True).click(timeout=10000)
    except PlaywrightTimeoutError:
        ensure_messaging_login(fresh, submitted=submitted)
        raise
    surface, editor = find_chat_editor(context, config["browserTimeout"])
    ensure_messaging_login(fresh, submitted=submitted)
    ensure_messaging_login(surface.page, submitted=submitted)
    return surface, editor


def find_chat_editor(context, timeout_ms):
    """Find the visible composer, including a newly opened page or iframe.

    A profile's 私信 button does not consistently mount the composer in the
    profile's main frame. Keep the diagnostics deliberately content-free:
    Actions logs are visible to repository readers.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        matches = []
        for page in context.pages:
            if page.is_closed():
                continue
            ensure_messaging_login(page)
            for frame in page.frames:
                if frame.is_detached():
                    continue
                editor = frame.locator('[contenteditable="true"]:visible')
                try:
                    count = editor.count()
                except PlaywrightError:
                    # Douyin replaces its chat iframe while loading. A stale
                    # frame is safe to skip here: no send has been attempted.
                    if frame.is_detached() or page.is_closed():
                        continue
                    raise
                if count > 1:
                    raise RuntimeError("Chat input is ambiguous; no message was sent")
                if count == 1:
                    matches.append((frame, editor))
        matches = [(frame, editor) for frame, editor in matches if not frame.is_detached()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RuntimeError("Chat input is ambiguous; no message was sent")
        time.sleep(0.5)

    for page in context.pages:
        if not page.is_closed():
            ensure_messaging_login(page)
    page_count = len([page for page in context.pages if not page.is_closed()])
    frame_count = sum(len(page.frames) for page in context.pages if not page.is_closed())
    raise ChatInputUnavailable(
        f"Chat input unavailable after opening 私信 (pages={page_count}, "
        f"frames={frame_count}); no message was sent"
    )


def run_target(context, target, match_mode, mode, message):
    target_id, profile_url = target_spec(target)
    search = context.new_page()
    profile = None
    try:
        if profile_url:
            # Douyin can keep loading media/analytics long after the profile
            # content is ready; waiting for the full load event can time out.
            search.goto(profile_url, wait_until="domcontentloaded")
            profile = search
        else:
            with context.expect_page() as opened:
                find_target_link(search, target_id, match_mode).click()
            profile = opened.value
        profile.wait_for_load_state("domcontentloaded")
        if match_mode == "short_id" or target_id.isdigit():
            profile.get_by_text(exact_id_pattern(target_id)).wait_for(timeout=config["browserTimeout"])
        for attempt in range(2):
            ensure_messaging_login(profile)
            try:
                profile.get_by_role("button", name="私信", exact=True).click(timeout=10000)
            except PlaywrightTimeoutError:
                ensure_messaging_login(profile)
                raise
            try:
                chat_surface, editor = find_chat_editor(
                    context, min(config["browserTimeout"], 20000) if attempt == 0
                    else config["browserTimeout"]
                )
                break
            except ChatInputUnavailable:
                if attempt == 1:
                    raise
                logger.info("CHAT_REOPEN: chat input not ready; no message entered or sent")
                for page in list(context.pages):
                    if page != profile and not page.is_closed():
                        page.close()
                profile.reload(wait_until="domcontentloaded")
                if match_mode == "short_id" or target_id.isdigit():
                    profile.get_by_text(exact_id_pattern(target_id)).wait_for(
                        timeout=config["browserTimeout"]
                    )
        # A one-off chat can display an optimistic composer while its IM
        # session is invalid. Require it to survive a fresh navigation before
        # any text is entered or submitted.
        verified_profile_url = profile_url or profile.url
        chat_surface, editor = open_fresh_chat(
            context, verified_profile_url, target_id, match_mode
        )
        if mode == "smoke":
            logger.info("SMOKE OK: target %s web chat survived fresh reopen; no message sent", target_id)
            return
        # Never auto-retry: a timeout after submission could duplicate a message.
        ensure_messaging_login(chat_surface.page)
        visible_messages = chat_surface.get_by_text(message, exact=True)
        before = visible_messages.count()
        editor.fill(message)
        editor.press("Enter")
        chat_surface.page.wait_for_timeout(1200)
        if editor.inner_text().strip("\u200b \r\n") or visible_messages.count() <= before:
            raise RuntimeError("Submission uncertain; do not auto-retry")
        # The web UI inserts an optimistic outgoing bubble even when the
        # server never stores the message. Reopen in a fresh page to verify
        # that the message can be read back from the account's chat history.
        chat_surface.page.wait_for_timeout(3000)
        fresh_surface, _ = open_fresh_chat(
            context, verified_profile_url, target_id, match_mode, submitted=True
        )
        if fresh_surface.get_by_text(message, exact=True).count() == 0:
            raise RuntimeError(
                "Outgoing bubble disappeared after reopening chat; "
                "server persistence unverified. Do not auto-retry"
            )
        logger.info("PERSISTED_SENDER_SIDE: target %s; recipient still needs checking", target_id)
    finally:
        for page in list(context.pages):
            if not page.is_closed():
                page.close()

def run_tasks(mode):
    if mode not in ("smoke", "send"):
        raise ValueError("RUN_MODE must be smoke or send")
    users = get_userData()
    if not users:
        raise RuntimeError("No usable TASKS and COOKIES_<UNIQUE_ID> configuration")
    match_mode = config.get("matchMode", "short_id")
    message = build_message() if mode == "send" else ""
    if mode == "send" and not message:
        raise RuntimeError("MESSAGE_TEMPLATE produced an empty message")
    playwright, browser = get_browser()
    try:
        for user in users:
            targets = user.get("targets", [])
            if not targets:
                raise RuntimeError(f"Account {user['username']} has no targets")
            context = browser.new_context()
            context.set_default_timeout(config["browserTimeout"])
            context.set_default_navigation_timeout(config["browserTimeout"])
            try:
                context.add_cookies(user["cookies"])
                owner = context.new_page()
                try:
                    verify_owner(owner, user["username"], user["unique_id"])
                finally:
                    owner.close()
                for target in targets:
                    run_target(context, target, match_mode, mode, message)
            finally:
                context.close()
    finally:
        browser.close()
        playwright.stop()
