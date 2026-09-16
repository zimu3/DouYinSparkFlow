"""Conservative automation for the ordinary douyin.com web chat UI.

The default mode is a non-sending smoke test. A send is attempted at most once
per target; a visible outgoing bubble is not treated as recipient delivery.
"""

import re
from urllib.parse import quote

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
    page.goto(f"{BASE_URL}/user/self")
    page.get_by_role("heading", name=username, exact=True).wait_for(timeout=config["browserTimeout"])
    if str(unique_id).isdigit():
        page.get_by_text(exact_id_pattern(unique_id)).wait_for(timeout=config["browserTimeout"])

def run_target(context, target, match_mode, mode, message):
    search = context.new_page()
    try:
        with context.expect_page() as opened:
            find_target_link(search, target, match_mode).click()
        profile = opened.value
        try:
            profile.wait_for_load_state("domcontentloaded")
            if match_mode == "short_id" or str(target).isdigit():
                profile.get_by_text(exact_id_pattern(target)).wait_for(timeout=config["browserTimeout"])
            profile.get_by_role("button", name="私信", exact=True).click()
            editor = profile.locator('[contenteditable="true"]:visible')
            editor.wait_for(timeout=config["browserTimeout"])
            if editor.count() != 1:
                raise RuntimeError("Chat input is ambiguous")
            if mode == "smoke":
                logger.info("SMOKE OK: target %s web chat opened; no message sent", target)
                return

            # Never auto-retry: a timeout after submission could duplicate a message.
            visible_messages = profile.get_by_text(message, exact=True)
            before = visible_messages.count()
            editor.fill(message)
            editor.press("Enter")
            profile.wait_for_timeout(1200)
            if editor.inner_text().strip("\u200b \r\n") or visible_messages.count() <= before:
                raise RuntimeError("Submission uncertain; do not auto-retry")
            logger.info("SUBMITTED_UNVERIFIED: target %s; check recipient app", target)
        finally:
            profile.close()
    finally:
        search.close()

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
