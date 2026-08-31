"""Route handlers for Guest Share Player."""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import TYPE_CHECKING, Any

from aiohttp import web

from .config import (
    CONF_CACHE_BYPASS,
    CONF_PUBLIC_BASE_URL,
    CONF_SITE_NAME,
    CONF_THEME_COLOR,
    DEFAULT_CACHE_BYPASS,
    DEFAULT_PUBLIC_BASE_URL,
    DEFAULT_SITE_NAME,
    DEFAULT_THEME_COLOR,
)
from .stream import stream_track_audio
from .templates import render_player_page

if TYPE_CHECKING:
    from . import GuestSharePlayerPlugin

LOGGER = logging.getLogger(__name__)


def get_image_url(plugin: GuestSharePlayerPlugin, item: Any, base_url: str) -> str:
    """Get best cover image URL for item."""
    img = None
    if hasattr(item, "image") and item.image:
        img = item.image
    elif hasattr(item, "metadata") and item.metadata and item.metadata.images:
        img = item.metadata.images[0]
    elif hasattr(item, "album") and item.album and hasattr(item.album, "image") and item.album.image:
        img = item.album.image

    if img:
        if hasattr(img, "path") and str(img.path).startswith("http"):
            return str(img.path)
        prov = getattr(img, "provider", "builtin")
        path = str(img.path)
        return f"/image_guest/{prov}/{urllib.parse.quote(path)}"

    return "/image_guest/builtin/placeholder"


async def handle_image_guest(plugin: GuestSharePlayerPlugin, request: web.Request) -> web.Response:
    """Serve image for guest player."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 3:
        return web.Response(status=400, text="Invalid image path")

    provider = parts[1]
    path = urllib.parse.unquote("/".join(parts[2:]))
    try:
        data = await plugin.mass.metadata.get_thumbnail(path=path, provider=provider)
        return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        LOGGER.debug("Serving placeholder for missing guest image %s: %s", path, e)
        svg_placeholder = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">'
            '<defs>'
            '<linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">'
            '<stop offset="0%" stop-color="#2a2523"/>'
            '<stop offset="100%" stop-color="#141210"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="500" height="500" rx="20" fill="url(#g)"/>'
            '<circle cx="250" cy="250" r="110" fill="none" stroke="#ff3366" stroke-width="6" opacity="0.4"/>'
            '<circle cx="250" cy="250" r="40" fill="#ff3366" opacity="0.6"/>'
            '<path d="M225 180v140a35 35 0 1 0 25 33.5V230l60-15v75a35 35 0 1 0 25 33.5V170l-110 25z" fill="#f8fafc" opacity="0.85"/>'
            '</svg>'
        )
        return web.Response(text=svg_placeholder, content_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


async def resolve_media_item(plugin: GuestSharePlayerPlugin, media_type: str, provider_id: str, item_id: str) -> Any:
    """Fetch media item from Music Assistant."""
    media_type = media_type.lower()
    if media_type in ("track", "tracks"):
        return await plugin.mass.music.tracks.get(item_id, provider_id)
    elif media_type in ("album", "albums"):
        return await plugin.mass.music.albums.get(item_id, provider_id)
    elif media_type in ("playlist", "playlists"):
        return await plugin.mass.music.playlists.get(item_id, provider_id)
    elif media_type in ("artist", "artists"):
        return await plugin.mass.music.artists.get(item_id, provider_id)
    return None


async def handle_share_view(plugin: GuestSharePlayerPlugin, request: web.Request) -> web.Response:
    """Serve the modern guest player web application with Discord Embed tags."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 4:
        return web.Response(text="Invalid share link format. Expected /s/<track|album|playlist>/<provider>/<id>", status=400)

    media_type = parts[1].lower().rstrip("s")
    provider_id = parts[2]
    item_id = "/".join(parts[3:])

    base_url = plugin.config.get_value(CONF_PUBLIC_BASE_URL, DEFAULT_PUBLIC_BASE_URL).rstrip("/")
    site_name = plugin.config.get_value(CONF_SITE_NAME, DEFAULT_SITE_NAME)
    theme_color = plugin.config.get_value(CONF_THEME_COLOR, DEFAULT_THEME_COLOR)

    try:
        item = await resolve_media_item(plugin, media_type, provider_id, item_id)
    except Exception as e:
        LOGGER.warning("Error resolving media item: %s", e)
        item = None

    if not item:
        title = f"{media_type.capitalize()} on {site_name}"
        artist_name = site_name
        image_url = f"{base_url}/favicon.ico"
    else:
        title = item.name
        artist_name = getattr(item, "artists", [None])[0].name if hasattr(item, "artists") and item.artists else ""
        if not artist_name and hasattr(item, "artist") and item.artist:
            artist_name = item.artist.name
        image_url = get_image_url(plugin, item, base_url)

    stream_url = f"/stream_guest/{media_type}/{provider_id}/{urllib.parse.quote(item_id)}"
    api_url = f"/api_guest/{media_type}/{provider_id}/{urllib.parse.quote(item_id)}"
    page_url = f"{base_url}{request.path}"

    html_text = render_player_page(
        media_type=media_type,
        title=title,
        artist_name=artist_name,
        image_url=image_url,
        stream_url=stream_url,
        api_url=api_url,
        page_url=page_url,
        site_name=site_name,
        theme_color=theme_color,
    )
    return web.Response(text=html_text, content_type="text/html")


async def handle_api_info(plugin: GuestSharePlayerPlugin, request: web.Request) -> web.Response:
    """Return JSON payload of track(s) for the player."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 4:
        return web.json_response({"error": "Invalid path"}, status=400)

    media_type = parts[1].lower().rstrip("s")
    provider_id = parts[2]
    item_id = "/".join(parts[3:])

    base_url = plugin.config.get_value(CONF_PUBLIC_BASE_URL, DEFAULT_PUBLIC_BASE_URL).rstrip("/")
    cache_bypass = plugin.config.get_value(CONF_CACHE_BYPASS, DEFAULT_CACHE_BYPASS)
    tracks_list = []

    try:
        if media_type == "album":
            album = await plugin.mass.music.albums.get(item_id, provider_id)
            tracks_gen = plugin.mass.music.albums.tracks(item_id, provider_id)
            tracks = [t async for t in tracks_gen]
            album_img = get_image_url(plugin, album, base_url)
            for t in tracks:
                art_name = t.artists[0].name if t.artists else album.artists[0].name if album.artists else ""
                pm = next(iter(t.provider_mappings)) if t.provider_mappings else None
                t_prov = pm.provider_instance if pm else provider_id
                t_id = pm.item_id if pm else t.item_id
                s_url = f"/stream_guest/track/{t_prov}/{urllib.parse.quote(str(t_id))}"
                if cache_bypass:
                    s_url += f"?v={int(time.time())}"
                tracks_list.append({
                    "name": t.name,
                    "artist": art_name,
                    "duration": t.duration,
                    "image": get_image_url(plugin, t, base_url) if hasattr(t, "image") and t.image else album_img,
                    "stream_url": s_url,
                })
        elif media_type == "playlist":
            playlist = await plugin.mass.music.playlists.get(item_id, provider_id)
            tracks_gen = plugin.mass.music.playlists.tracks(item_id, provider_id)
            tracks = [t async for t in tracks_gen]
            pl_img = get_image_url(plugin, playlist, base_url)
            for t in tracks:
                art_name = t.artists[0].name if t.artists else ""
                pm = next(iter(t.provider_mappings)) if t.provider_mappings else None
                t_prov = pm.provider_instance if pm else provider_id
                t_id = pm.item_id if pm else t.item_id
                s_url = f"/stream_guest/track/{t_prov}/{urllib.parse.quote(str(t_id))}"
                if cache_bypass:
                    s_url += f"?v={int(time.time())}"
                tracks_list.append({
                    "name": t.name,
                    "artist": art_name,
                    "duration": t.duration,
                    "image": get_image_url(plugin, t, base_url) if hasattr(t, "image") and t.image else pl_img,
                    "stream_url": s_url,
                })
        else:  # track
            track = await plugin.mass.music.tracks.get(item_id, provider_id)
            art_name = track.artists[0].name if track.artists else ""
            pm = next(iter(track.provider_mappings)) if track.provider_mappings else None
            t_prov = pm.provider_instance if pm else provider_id
            t_id = pm.item_id if pm else track.item_id
            s_url = f"/stream_guest/track/{t_prov}/{urllib.parse.quote(str(t_id))}"
            if cache_bypass:
                s_url += f"?v={int(time.time())}"
            tracks_list.append({
                "name": track.name,
                "artist": art_name,
                "duration": track.duration,
                "image": get_image_url(plugin, track, base_url),
                "stream_url": s_url,
            })
    except Exception as e:
        LOGGER.exception("Error preparing guest api payload: %s", e)
        return web.json_response({"error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

    return web.json_response({"tracks": tracks_list}, headers={"Access-Control-Allow-Origin": "*"})


async def handle_stream_audio(plugin: GuestSharePlayerPlugin, request: web.Request) -> web.StreamResponse:
    """Stream real-time audio."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 4:
        return web.Response(text="Invalid stream URL", status=400)

    provider_id = parts[2]
    item_id = urllib.parse.unquote("/".join(parts[3:]))
    cache_bypass = plugin.config.get_value(CONF_CACHE_BYPASS, DEFAULT_CACHE_BYPASS)
    return await stream_track_audio(plugin.mass, request, provider_id, item_id, cache_bypass=cache_bypass)
