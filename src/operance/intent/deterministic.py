"""Minimal deterministic matcher for the Phase 0A seed commands."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from ..key_presses import normalize_supported_key
from ..launch_targets import is_url_like_target, normalize_explicit_url_target
from ..models.actions import ActionPlan, PlanSource, RiskTier, ToolName, TypedAction
from ..registry import derive_action_safety_metadata
from ..skills import SkillLibrary, action_plan_from_skill_command, build_default_skill_library
from .speech_recovery import recover_spoken_app_target


def _normalize_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"[?!,]+", "", normalized)
    normalized = normalized.rstrip(".")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _normalize_explicit_url_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"[?!,]+", "", normalized)
    normalized = normalized.rstrip(".")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _normalize_spoken_launch_target(value: str) -> str:
    candidate = value.strip()
    localhost_match = re.fullmatch(r"((?:localhost|127\.0\.0\.1))(?: port)? (\d+)", candidate)
    if localhost_match:
        return f"{localhost_match.group(1)}:{localhost_match.group(2)}"
    normalized_candidate = candidate.casefold()
    browser_aliases = {
        "the browser": "browser",
        "my browser": "browser",
        "the web browser": "web browser",
        "my web browser": "web browser",
        "the default browser": "default browser",
        "the default web browser": "default browser",
        "default web browser": "default browser",
    }
    if normalized_candidate in browser_aliases:
        return browser_aliases[normalized_candidate]
    if normalized_candidate in {"the terminal", "my terminal"}:
        return "terminal"
    return candidate


def _normalize_spoken_app_target(value: str) -> str:
    candidate = _normalize_spoken_launch_target(value)
    return recover_spoken_app_target(candidate)


def _google_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query.strip())}"


def _is_simple_app_phrase(value: str, *, allow_url_like: bool = False) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    if candidate.startswith("window "):
        return False
    if candidate.startswith(
        (
            "file on desktop called ",
            "folder on desktop called ",
            "item on desktop called ",
            "recent file called ",
        )
    ):
        return False
    normalized_candidate = _normalize_spoken_launch_target(candidate)
    if not allow_url_like and is_url_like_target(normalized_candidate):
        return False
    return not bool(re.search(r"\b(and|then)\b", candidate))


def _normalize_chain_url_target(verb: str, target: str) -> str | None:
    normalized_target = _normalize_spoken_launch_target(target)
    if verb == "open":
        return normalized_target if is_url_like_target(normalized_target) else None

    explicit_target = normalize_explicit_url_target(normalized_target)
    return explicit_target if is_url_like_target(explicit_target) else None


@dataclass(slots=True)
class DeterministicIntentMatcher:
    """Map known transcript strings to a single typed action plan."""

    skill_library: SkillLibrary = field(default_factory=build_default_skill_library)

    def match(self, text: str) -> ActionPlan | None:
        normalized = _normalize_text(text)
        explicit_url_text = _normalize_explicit_url_text(text)

        skill_command = self.skill_library.match(text)
        if skill_command is not None:
            return action_plan_from_skill_command(skill_command, text)

        two_step_launch_plan = self._two_step_launch_plan(text, normalized)
        if two_step_launch_plan is not None:
            return two_step_launch_plan

        launch_notify_plan = self._launch_notify_plan(text, normalized)
        if launch_notify_plan is not None:
            return launch_notify_plan

        search_match = re.fullmatch(
            r"(?:search google for|google search for|search(?: the)? web for|web search for|search for|look up) (.+)",
            normalized,
        )
        if search_match:
            query = search_match.group(1).strip()
            if query:
                return self._single_action_plan(
                    text,
                    ToolName.APPS_LAUNCH,
                    args={"app": _google_search_url(query)},
                )

        folder_location_match = re.fullmatch(
            r"(?:open|show) (?:(desktop|downloads|documents|home)(?: folder)?|folder (desktop|downloads|documents|home))",
            normalized,
        )
        if folder_location_match:
            location = folder_location_match.group(1) or folder_location_match.group(2)
            return self._single_action_plan(
                text,
                ToolName.FILES_OPEN,
                args={"location": location},
            )

        if normalized in {"open firefox", "launch firefox"}:
            return self._single_action_plan(
                text,
                ToolName.APPS_LAUNCH,
                args={"app": "firefox"},
            )

        if normalized in {"open terminal", "please open terminal", "launch terminal"}:
            return self._single_action_plan(
                text,
                ToolName.APPS_LAUNCH,
                args={"app": "terminal"},
            )

        browse_target_match = re.fullmatch(r"browse to (.+)", explicit_url_text)
        if browse_target_match:
            target = normalize_explicit_url_target(_normalize_spoken_launch_target(browse_target_match.group(1)))
            if _is_simple_app_phrase(target, allow_url_like=True):
                return self._single_action_plan(
                    text,
                    ToolName.APPS_LAUNCH,
                    args={"app": target},
                )

        open_url_match = re.fullmatch(r"open url (.+)", explicit_url_text)
        if open_url_match:
            target = normalize_explicit_url_target(_normalize_spoken_launch_target(open_url_match.group(1)))
            if _is_simple_app_phrase(target, allow_url_like=True):
                return self._single_action_plan(
                    text,
                    ToolName.APPS_LAUNCH,
                    args={"app": target},
                )

        navigate_target_match = re.fullmatch(r"(?:go to|visit|open (?:website|site)) (.+)", explicit_url_text)
        if navigate_target_match:
            target = normalize_explicit_url_target(_normalize_spoken_launch_target(navigate_target_match.group(1)))
            if is_url_like_target(target) and _is_simple_app_phrase(target, allow_url_like=True):
                return self._single_action_plan(
                    text,
                    ToolName.APPS_LAUNCH,
                    args={"app": target},
                )

        launch_app_match = re.fullmatch(r"(?:please )?(?:open|launch)(?: app)? (.+)", normalized)
        if launch_app_match:
            target = _normalize_spoken_app_target(launch_app_match.group(1))
            if _is_simple_app_phrase(target, allow_url_like=True):
                return self._single_action_plan(
                    text,
                    ToolName.APPS_LAUNCH,
                    args={"app": target},
                )

        if normalized in {"focus firefox", "switch to firefox"}:
            return self._single_action_plan(
                text,
                ToolName.APPS_FOCUS,
                args={"app": "firefox"},
            )

        if normalized in {"focus terminal", "switch to terminal"}:
            return self._single_action_plan(
                text,
                ToolName.APPS_FOCUS,
                args={"app": "terminal"},
            )

        quit_app_match = re.fullmatch(r"quit( app)? (.+)", normalized)
        if quit_app_match:
            target = _normalize_spoken_app_target(quit_app_match.group(2))
            if not _is_simple_app_phrase(target):
                return None
            return self._single_action_plan(
                text,
                ToolName.APPS_QUIT,
                args={"app": target},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        if normalized in {
            "list windows",
            "show windows",
            "show open windows",
            "list open windows",
            "what windows are open",
            "what apps are open",
            "show open apps",
            "list open apps",
        }:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_LIST,
            )

        window_find_match = (
            re.fullmatch(r"is (.+) open", normalized)
            or re.fullmatch(r"is (.+) running", normalized)
            or re.fullmatch(r"is window (.+) open", normalized)
            or re.fullmatch(r"find window (.+)", normalized)
            or re.fullmatch(r"show windows matching (.+)", normalized)
        )
        if window_find_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_FIND,
                args={"window": window_find_match.group(1)},
            )

        window_switch_match = re.fullmatch(r"switch to window (.+)", normalized) or re.fullmatch(
            r"switch to (.+) window", normalized
        )
        if window_switch_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SWITCH,
                args={"window": window_switch_match.group(1)},
            )

        focus_app_match = re.fullmatch(r"(?:please )?(?:focus|switch to)(?: app)? (.+)", normalized)
        if focus_app_match:
            target = _normalize_spoken_app_target(focus_app_match.group(1))
            if not _is_simple_app_phrase(target):
                return None
            return self._single_action_plan(
                text,
                ToolName.APPS_FOCUS,
                args={"app": target},
            )

        window_minimize_match = re.fullmatch(r"minimize window (.+)", normalized)
        if window_minimize_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_MINIMIZE,
                args={"window": window_minimize_match.group(1)},
                risk_tier=RiskTier.TIER_1,
            )

        window_maximize_match = re.fullmatch(r"maximize window (.+)", normalized)
        if window_maximize_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_MAXIMIZE,
                args={"window": window_maximize_match.group(1)},
                risk_tier=RiskTier.TIER_1,
            )

        window_fullscreen_match = re.fullmatch(r"fullscreen window (.+)", normalized) or re.fullmatch(
            r"make window (.+) fullscreen", normalized
        )
        if window_fullscreen_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_FULLSCREEN,
                args={"window": window_fullscreen_match.group(1), "enabled": True},
                risk_tier=RiskTier.TIER_1,
            )

        window_exit_fullscreen_match = re.fullmatch(r"exit fullscreen for window (.+)", normalized) or re.fullmatch(
            r"leave fullscreen for window (.+)", normalized
        )
        if window_exit_fullscreen_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_FULLSCREEN,
                args={"window": window_exit_fullscreen_match.group(1), "enabled": False},
                risk_tier=RiskTier.TIER_1,
            )

        window_keep_above_match = re.fullmatch(r"keep window (.+) above", normalized) or re.fullmatch(
            r"keep (.+) above", normalized
        )
        if window_keep_above_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_KEEP_ABOVE,
                args={"window": window_keep_above_match.group(1), "enabled": True},
                risk_tier=RiskTier.TIER_1,
            )

        window_disable_keep_above_match = re.fullmatch(
            r"stop keeping window (.+) above", normalized
        ) or re.fullmatch(r"stop keeping (.+) above", normalized)
        if window_disable_keep_above_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_KEEP_ABOVE,
                args={"window": window_disable_keep_above_match.group(1), "enabled": False},
                risk_tier=RiskTier.TIER_1,
            )

        window_shade_match = re.fullmatch(r"shade window (.+)", normalized)
        if window_shade_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_SHADED,
                args={"window": window_shade_match.group(1), "enabled": True},
                risk_tier=RiskTier.TIER_1,
            )

        window_unshade_match = re.fullmatch(r"unshade window (.+)", normalized)
        if window_unshade_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_SHADED,
                args={"window": window_unshade_match.group(1), "enabled": False},
                risk_tier=RiskTier.TIER_1,
            )

        window_keep_below_match = re.fullmatch(r"keep window (.+) below", normalized) or re.fullmatch(
            r"keep (.+) below", normalized
        )
        if window_keep_below_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_KEEP_BELOW,
                args={"window": window_keep_below_match.group(1), "enabled": True},
                risk_tier=RiskTier.TIER_1,
            )

        window_disable_keep_below_match = re.fullmatch(
            r"stop keeping window (.+) below", normalized
        ) or re.fullmatch(r"stop keeping (.+) below", normalized)
        if window_disable_keep_below_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_KEEP_BELOW,
                args={"window": window_disable_keep_below_match.group(1), "enabled": False},
                risk_tier=RiskTier.TIER_1,
            )

        window_all_desktops_match = re.fullmatch(r"show window (.+) on all desktops", normalized) or re.fullmatch(
            r"keep window (.+) on all desktops", normalized
        )
        if window_all_desktops_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
                args={"window": window_all_desktops_match.group(1), "enabled": True},
                risk_tier=RiskTier.TIER_1,
            )

        window_current_desktop_only_match = re.fullmatch(
            r"show window (.+) only on this desktop", normalized
        )
        if window_current_desktop_only_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_SET_ON_ALL_DESKTOPS,
                args={"window": window_current_desktop_only_match.group(1), "enabled": False},
                risk_tier=RiskTier.TIER_1,
            )

        window_restore_match = re.fullmatch(r"restore window (.+)", normalized)
        if window_restore_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_RESTORE,
                args={"window": window_restore_match.group(1)},
                risk_tier=RiskTier.TIER_1,
            )

        window_close_match = re.fullmatch(r"close window (.+)", normalized)
        if window_close_match:
            return self._single_action_plan(
                text,
                ToolName.WINDOWS_CLOSE,
                args={"window": window_close_match.group(1)},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        if normalized in {"what time is it", "tell me the time", "current time", "time"}:
            return self._single_action_plan(text, ToolName.TIME_NOW)

        if normalized in {"what is my battery level", "battery status", "battery level", "battery"}:
            return self._single_action_plan(text, ToolName.POWER_BATTERY_STATUS)

        if normalized in {"what is the volume", "current volume", "get volume", "volume"}:
            return self._single_action_plan(text, ToolName.AUDIO_GET_VOLUME)

        if normalized in {"is audio muted", "is the audio muted", "audio mute status", "muted"}:
            return self._single_action_plan(text, ToolName.AUDIO_MUTE_STATUS)

        if normalized in {"what is on the clipboard", "read clipboard", "read the clipboard"}:
            return self._single_action_plan(text, ToolName.CLIPBOARD_GET_TEXT)

        clipboard_copy_match = re.fullmatch(r"copy (.+) to clipboard", normalized)
        if clipboard_copy_match:
            return self._single_action_plan(
                text,
                ToolName.CLIPBOARD_SET_TEXT,
                args={"text": clipboard_copy_match.group(1)},
                risk_tier=RiskTier.TIER_1,
            )

        if normalized in {"copy selection", "copy selected text"}:
            return self._single_action_plan(
                text,
                ToolName.CLIPBOARD_COPY_SELECTION,
                risk_tier=RiskTier.TIER_1,
            )

        if normalized in {"clear clipboard", "empty clipboard"}:
            return self._single_action_plan(
                text,
                ToolName.CLIPBOARD_CLEAR,
                risk_tier=RiskTier.TIER_1,
            )

        if normalized in {"paste clipboard", "paste from clipboard"}:
            return self._single_action_plan(
                text,
                ToolName.CLIPBOARD_PASTE,
                risk_tier=RiskTier.TIER_1,
            )

        typed_text_match = re.fullmatch(r"type (.+)", normalized)
        if typed_text_match:
            return self._single_action_plan(
                text,
                ToolName.TEXT_TYPE,
                args={"text": typed_text_match.group(1)},
                risk_tier=RiskTier.TIER_1,
            )

        key_press_match = re.fullmatch(r"(?:press|hit) (.+)", normalized)
        if key_press_match:
            normalized_key = normalize_supported_key(key_press_match.group(1))
            if normalized_key is None:
                return None
            return self._single_action_plan(
                text,
                ToolName.KEYS_PRESS,
                args={"key": normalized_key},
                risk_tier=RiskTier.TIER_1,
            )

        if normalized in {"wifi status", "what is the wifi status", "what is the wi fi status"}:
            return self._single_action_plan(text, ToolName.NETWORK_WIFI_STATUS)

        if normalized in {
            "disconnect wifi",
            "disconnect wi fi",
            "disconnect from wifi",
            "disconnect from wi fi",
        }:
            return self._single_action_plan(
                text,
                ToolName.NETWORK_DISCONNECT_CURRENT,
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        connect_wifi_match = re.fullmatch(r"connect to (wi fi|wifi) (.+)", normalized)
        if connect_wifi_match:
            return self._single_action_plan(
                text,
                ToolName.NETWORK_CONNECT_KNOWN_SSID,
                args={"ssid": connect_wifi_match.group(2)},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        volume_match = (
            re.fullmatch(r"set( the)? volume to (\d{1,3}) percent", normalized)
            or re.fullmatch(r"set( the)? volume (\d{1,3})(?: percent)?", normalized)
            or re.fullmatch(r"volume (\d{1,3}) percent", normalized)
        )
        if volume_match:
            percent = int(volume_match.groups()[-1])
            if 0 <= percent <= 100:
                risk_tier, requires_confirmation = derive_action_safety_metadata(
                    ToolName.AUDIO_SET_VOLUME,
                    {"percent": percent},
                    base_risk_tier=RiskTier.TIER_1,
                    requires_confirmation=False,
                )
                return self._single_action_plan(
                    text,
                    ToolName.AUDIO_SET_VOLUME,
                    args={"percent": percent},
                    risk_tier=risk_tier,
                    requires_confirmation=requires_confirmation,
                )

        if normalized in {"mute audio", "mute sound", "mute"}:
            return self._single_action_plan(
                text,
                ToolName.AUDIO_SET_MUTED,
                args={"muted": True},
                risk_tier=RiskTier.TIER_1,
            )

        if normalized in {"unmute audio", "unmute sound", "unmute"}:
            return self._single_action_plan(
                text,
                ToolName.AUDIO_SET_MUTED,
                args={"muted": False},
                risk_tier=RiskTier.TIER_1,
            )

        wifi_match = re.fullmatch(r"turn( the)? wi fi (on|off)", normalized) or re.fullmatch(
            r"turn( the)? wifi (on|off)", normalized
        ) or re.fullmatch(
            r"turn (on|off) wifi", normalized
        )
        if wifi_match:
            state_group = wifi_match.groups()[-1]
            enabled = state_group == "on"
            risk_tier, requires_confirmation = derive_action_safety_metadata(
                ToolName.NETWORK_SET_WIFI_ENABLED,
                {"enabled": enabled},
                base_risk_tier=RiskTier.TIER_1,
                requires_confirmation=False,
            )
            return self._single_action_plan(
                text,
                ToolName.NETWORK_SET_WIFI_ENABLED,
                args={"enabled": enabled},
                risk_tier=risk_tier,
                requires_confirmation=requires_confirmation,
            )

        notification_match = re.fullmatch(r"show( a)? notification saying (.+)", normalized)
        if notification_match:
            return self._single_action_plan(
                text,
                ToolName.NOTIFICATIONS_SHOW,
                args={"title": "Operance", "message": notification_match.group(2)},
            )

        if normalized in {"show files modified today", "show recent files"}:
            return self._single_action_plan(
                text,
                ToolName.FILES_LIST_RECENT,
                args={"modified_since": "today"},
            )

        list_folder_match = (
            re.fullmatch(r"(?:list|show) files in (desktop|downloads|documents|home)", normalized)
            or re.fullmatch(r"(?:list|show) (desktop|downloads|documents|home) files", normalized)
            or re.fullmatch(r"what(?: is|'s) in (desktop|downloads|documents|home)", normalized)
        )
        if list_folder_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_LIST_FOLDER,
                args={"location": list_folder_match.group(1)},
            )

        find_named_match = re.fullmatch(
            r"find (file|folder|item) named (.+?)(?: in (desktop|downloads|documents|home))?",
            normalized,
        )
        if find_named_match:
            kind_by_word = {"file": "file", "folder": "folder", "item": "any"}
            return self._single_action_plan(
                text,
                ToolName.FILES_FIND,
                args={
                    "location": find_named_match.group(3) or "home",
                    "query": find_named_match.group(2),
                    "kind": kind_by_word[find_named_match.group(1)],
                },
            )

        search_folder_match = re.fullmatch(
            r"search (desktop|downloads|documents|home) for (.+)",
            normalized,
        )
        if search_folder_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_FIND,
                args={
                    "location": search_folder_match.group(1),
                    "query": search_folder_match.group(2),
                    "kind": "any",
                },
            )

        recent_folder_match = (
            re.fullmatch(r"show recent files in (desktop|downloads|documents|home)", normalized)
            or re.fullmatch(r"show recent (desktop|downloads|documents|home)(?: files| entries)?", normalized)
            or re.fullmatch(r"recent (desktop|downloads|documents|home)", normalized)
        )
        if recent_folder_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_LIST_RECENT_FOLDER,
                args={"location": recent_folder_match.group(1)},
            )

        details_match = (
            re.fullmatch(r"(?:show|display) details for (.+?)(?: in (desktop|downloads|documents|home))?", normalized)
            or re.fullmatch(r"file details for (.+?)(?: in (desktop|downloads|documents|home))?", normalized)
        )
        if details_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_GET_INFO,
                args={
                    "location": details_match.group(2) or "home",
                    "query": details_match.group(1),
                    "kind": "any",
                },
            )

        file_size_match = re.fullmatch(
            r"how big is (.+?)(?: in (desktop|downloads|documents|home))?",
            normalized,
        )
        if file_size_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_GET_INFO,
                args={
                    "location": file_size_match.group(2) or "home",
                    "query": file_size_match.group(1),
                    "kind": "file",
                },
            )

        modified_match = re.fullmatch(
            r"when was (.+?) (?:last )?modified(?: in (desktop|downloads|documents|home))?",
            normalized,
        )
        if modified_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_GET_INFO,
                args={
                    "location": modified_match.group(2) or "home",
                    "query": modified_match.group(1),
                    "kind": "any",
                },
            )

        open_recent_file_match = re.fullmatch(r"open recent file called (.+)", normalized)
        if open_recent_file_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_OPEN,
                args={"location": "recent", "name": open_recent_file_match.group(1)},
            )

        open_entry_match = re.fullmatch(r"open (file|folder|item) on desktop called (.+)", normalized)
        if open_entry_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_OPEN,
                args={"location": "desktop", "name": open_entry_match.group(2)},
            )

        folder_match = re.fullmatch(r"(create|make)( a)? folder on desktop called (.+)", normalized)
        if folder_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_CREATE_FOLDER,
                args={"location": "desktop", "name": folder_match.group(3)},
                risk_tier=RiskTier.TIER_1,
            )

        delete_folder_match = re.fullmatch(r"delete folder on desktop called (.+)", normalized)
        if delete_folder_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_DELETE_FOLDER,
                args={"location": "desktop", "name": delete_folder_match.group(1)},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        delete_file_match = re.fullmatch(r"delete file on desktop called (.+)", normalized)
        if delete_file_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_DELETE_FILE,
                args={"location": "desktop", "name": delete_file_match.group(1)},
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        rename_entry_match = re.fullmatch(
            r"rename (file|folder|item) on desktop from (.+) to (.+)",
            normalized,
        )
        if rename_entry_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_RENAME,
                args={
                    "location": "desktop",
                    "source_name": rename_entry_match.group(2),
                    "target_name": rename_entry_match.group(3),
                },
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        move_entry_match = re.fullmatch(
            r"move (file|folder|item) on desktop called (.+) to (.+)",
            normalized,
        )
        if move_entry_match:
            return self._single_action_plan(
                text,
                ToolName.FILES_MOVE,
                args={
                    "location": "desktop",
                    "name": move_entry_match.group(2),
                    "destination_folder": move_entry_match.group(3),
                },
                risk_tier=RiskTier.TIER_2,
                requires_confirmation=True,
            )

        return None

    def _two_step_launch_plan(self, original_text: str, normalized: str) -> ActionPlan | None:
        launch_chain_match = re.fullmatch(
            r"(?:please )?(?:open|launch)(?: app)? (.+?) (?:and|then) (open url|browse to|load|open) (.+)",
            normalized,
        )
        if not launch_chain_match:
            return None

        app_target = _normalize_spoken_app_target(launch_chain_match.group(1))
        url_target = _normalize_chain_url_target(launch_chain_match.group(2), launch_chain_match.group(3))
        if url_target is None or not _is_simple_app_phrase(app_target):
            return None

        return ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=original_text,
            actions=[
                TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": app_target}),
                TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": url_target}),
            ],
        )

    def _launch_notify_plan(self, original_text: str, normalized: str) -> ActionPlan | None:
        launch_notify_match = re.fullmatch(
            r"(?:please )?(?:open|launch|start)(?: app)? (.+?) (?:and|then) notify me",
            normalized,
        )
        if not launch_notify_match:
            return None

        app_target = _normalize_spoken_app_target(launch_notify_match.group(1))
        if not _is_simple_app_phrase(app_target, allow_url_like=True):
            return None

        return ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=original_text,
            actions=[
                TypedAction(tool=ToolName.APPS_LAUNCH, args={"app": app_target}),
                TypedAction(
                    tool=ToolName.NOTIFICATIONS_SHOW,
                    args={"title": "Opened", "message": f"{app_target} opened"},
                ),
            ],
        )

    def _single_action_plan(
        self,
        original_text: str,
        tool: ToolName,
        *,
        args: dict[str, object] | None = None,
        risk_tier: RiskTier = RiskTier.TIER_0,
        requires_confirmation: bool = False,
    ) -> ActionPlan:
        return ActionPlan(
            source=PlanSource.DETERMINISTIC,
            original_text=original_text,
            actions=[
                TypedAction(
                    tool=tool,
                    args=args or {},
                    risk_tier=risk_tier,
                    requires_confirmation=requires_confirmation,
                )
            ],
        )
