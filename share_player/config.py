"""Configuration definitions for Guest Share Player."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant_models.config_entries import ConfigEntry, ConfigValueType

CONF_PUBLIC_BASE_URL = "public_base_url"
CONF_SITE_NAME = "site_name"
CONF_THEME_COLOR = "theme_color"
CONF_CACHE_BYPASS = "cache_bypass"
CONF_EMBED_TITLE_TEMPLATE = "embed_title_template"
CONF_EMBED_DESC_TEMPLATE = "embed_desc_template"
CONF_EMBED_FOOTER_TEMPLATE = "embed_footer_template"

DEFAULT_PUBLIC_BASE_URL = "https://m.minopia.de"
DEFAULT_SITE_NAME = "Music Assistant"
DEFAULT_THEME_COLOR = "#3080ff"
DEFAULT_CACHE_BYPASS = True
DEFAULT_EMBED_TITLE_TEMPLATE = "{title}"
DEFAULT_EMBED_DESC_TEMPLATE = "🎵 {media_type_label} by {artist}{duration_str}"
DEFAULT_EMBED_FOOTER_TEMPLATE = ""


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
            label="Player & Embed Accent Color (Hex)",
            default_value=DEFAULT_THEME_COLOR,
            description="Hex accent color for playback controls, progress bar, and Discord embed sidebar (e.g. #3080ff).",
            required=False,
        ),
        ConfigEntry(
            key=CONF_CACHE_BYPASS,
            type=ConfigEntryType.BOOLEAN,
            label="Enable CDN / Browser Cache Bypass",
            default_value=DEFAULT_CACHE_BYPASS,
            description="Appends anti-caching query parameters and strict no-store headers to audio stream requests to prevent Cloudflare and CDNs from caching audio or error responses.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_TITLE_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Title Template",
            default_value=DEFAULT_EMBED_TITLE_TEMPLATE,
            description="Title template for embeds. Variables: {title}, {artist}, {site_name}, {media_type}.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_DESC_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Description Template",
            default_value=DEFAULT_EMBED_DESC_TEMPLATE,
            description="Description template for embeds. Variables: {title}, {artist}, {site_name}, {media_type}, {media_type_label}, {duration}, {duration_str}.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_FOOTER_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Footer / Call-to-action (Optional)",
            default_value=DEFAULT_EMBED_FOOTER_TEMPLATE,
            description="Optional extra text appended to embed description (leave blank for none). Variables: {site_name}.",
            required=False,
        ),
    )
