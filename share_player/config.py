"""Configuration definitions for Guest Share Player."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigEntry, ConfigValueType
    from music_assistant.mass import MusicAssistant

CONF_PUBLIC_BASE_URL = "public_base_url"
CONF_SITE_NAME = "site_name"
CONF_THEME_COLOR = "theme_color"

DEFAULT_PUBLIC_BASE_URL = "https://m.minopia.de"
DEFAULT_SITE_NAME = "Music Assistant"
DEFAULT_THEME_COLOR = "#FF3366"


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """Return Config entries to setup this provider."""
    from music_assistant_models.config_entries import ConfigEntry, ConfigEntryType

    return (
        ConfigEntry(
            key=CONF_PUBLIC_BASE_URL,
            type=ConfigEntryType.STRING,
            label="Public Base URL",
            default_value=DEFAULT_PUBLIC_BASE_URL,
            description="The public URL where your player is reached (e.g. https://m.minopia.de or https://music.minopia.de). Used for Discord embed meta tags.",
            required=True,
        ),
        ConfigEntry(
            key=CONF_SITE_NAME,
            type=ConfigEntryType.STRING,
            label="Site / Service Name",
            default_value=DEFAULT_SITE_NAME,
            description="Brand name displayed in Discord embed header and browser tabs.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_THEME_COLOR,
            type=ConfigEntryType.STRING,
            label="Embed Accent Color (Hex)",
            default_value=DEFAULT_THEME_COLOR,
            description="Hex color code for Discord embed sidebar (e.g. #FF3366).",
            required=False,
        ),
    )
