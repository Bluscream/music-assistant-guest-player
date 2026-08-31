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
CONF_AUTOPLAY = "autoplay"
CONF_EMBED_AUTHOR_TEMPLATE = "embed_author_template"
CONF_EMBED_TITLE_TEMPLATE = "embed_title_template"
CONF_EMBED_DESC_TEMPLATE = "embed_desc_template"
CONF_EMBED_FOOTER_TEMPLATE = "embed_footer_template"

DEFAULT_PUBLIC_BASE_URL = ""
DEFAULT_SITE_NAME = "Music Assistant"
DEFAULT_THEME_COLOR = "#3080ff"
DEFAULT_CACHE_BYPASS = True
DEFAULT_AUTOPLAY = False
DEFAULT_EMBED_AUTHOR_TEMPLATE = "{site_name}"
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
            label="Public Base URL (Optional Override)",
            default_value=DEFAULT_PUBLIC_BASE_URL,
            description="Explicit public URL (e.g. https://music.minopia.de). If left blank, it is auto-detected dynamically from the incoming browser/Discord request.",
            required=False,
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
            key=CONF_AUTOPLAY,
            type=ConfigEntryType.BOOLEAN,
            label="Autoplay on Page Load",
            default_value=DEFAULT_AUTOPLAY,
            description="Automatically begin audio playback as soon as the web player loads (subject to browser autoplay policies).",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_AUTHOR_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Author / Site Name Template",
            default_value=DEFAULT_EMBED_AUTHOR_TEMPLATE,
            description="Template for the top embed author line. Variables: {site_name}, {artist}, {album}, {title}, {provider}.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_TITLE_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Title Template",
            default_value=DEFAULT_EMBED_TITLE_TEMPLATE,
            description="Title template for embeds. Variables: {title}, {artist}, {album}, {site_name}, {media_type}, {media_type_label}, {year}.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_DESC_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Description Template",
            default_value=DEFAULT_EMBED_DESC_TEMPLATE,
            description="Description template for embeds. Variables: {title}, {artist}, {album}, {site_name}, {media_type}, {media_type_label}, {duration}, {duration_str}, {year}, {provider}.",
            required=False,
        ),
        ConfigEntry(
            key=CONF_EMBED_FOOTER_TEMPLATE,
            type=ConfigEntryType.STRING,
            label="Embed Footer / Call-to-action (Optional)",
            default_value=DEFAULT_EMBED_FOOTER_TEMPLATE,
            description="Optional extra text appended to embed description (leave blank for none). Variables: {site_name}, {title}, {artist}, {album}, {media_type_label}.",
            required=False,
        ),
    )
