"""Route handlers for Guest Player."""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import TYPE_CHECKING, Any

from aiohttp import web

from .config import (
    CONF_AUTOPLAY,
    CONF_CACHE_BYPASS,
    CONF_EMBED_AUTHOR_TEMPLATE,
    CONF_EMBED_DESC_TEMPLATE,
    CONF_EMBED_FOOTER_TEMPLATE,
    CONF_EMBED_TITLE_TEMPLATE,
    CONF_PUBLIC_BASE_URL,
    CONF_SITE_NAME,
    CONF_THEME_COLOR,
    DEFAULT_AUTOPLAY,
    DEFAULT_CACHE_BYPASS,
    DEFAULT_EMBED_AUTHOR_TEMPLATE,
    DEFAULT_EMBED_DESC_TEMPLATE,
    DEFAULT_EMBED_FOOTER_TEMPLATE,
    DEFAULT_EMBED_TITLE_TEMPLATE,
    DEFAULT_PUBLIC_BASE_URL,
    DEFAULT_SITE_NAME,
    DEFAULT_THEME_COLOR,
)
from .stream import stream_track_audio
from .templates import (
    render_link_generator_page,
    render_player_page,
    render_svg_placeholder,
)

if TYPE_CHECKING:
    from . import GuestPlayerPlugin

LOGGER = logging.getLogger(__name__)


def get_request_base_url(plugin: GuestPlayerPlugin, request: web.Request) -> str:
    """Resolve public base URL from config or incoming request headers dynamically."""
    configured = plugin.config.get_value(CONF_PUBLIC_BASE_URL, DEFAULT_PUBLIC_BASE_URL)
    if configured and str(configured).strip():
        return str(configured).strip().rstrip("/")

    # Dynamic auto-detection via standard reverse-proxy headers
    proto = request.headers.get("X-Forwarded-Proto", request.scheme or "http")
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{proto}://{host}".rstrip("/")


def get_image_url(plugin: GuestPlayerPlugin, item: Any, base_url: str) -> str:
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


async def handle_image_guest(plugin: GuestPlayerPlugin, request: web.Request) -> web.Response:
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
        theme_color = plugin.config.get_value(CONF_THEME_COLOR, DEFAULT_THEME_COLOR)
        svg_placeholder = render_svg_placeholder(theme_color)
        return web.Response(text=svg_placeholder, content_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


async def resolve_media_item(plugin: GuestPlayerPlugin, media_type: str, provider_id: str, item_id: str) -> Any:
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
    elif media_type in ("radio", "radios"):
        return await plugin.mass.music.radio.get(item_id, provider_id)
    return None


def normalize_media_type(media_type: str) -> str:
    """Normalize plural/singular media type string."""
    mt = media_type.lower()
    mapping = {
        "tracks": "track",
        "albums": "album",
        "playlists": "playlist",
        "artists": "artist",
        "radios": "radio",
    }
    return mapping.get(mt, mt)


async def handle_share_view(plugin: GuestPlayerPlugin, request: web.Request) -> web.Response:
    """Serve the modern guest player web application with Discord Embed tags, or link generator at /s."""
    parts = [p for p in request.path.split("/") if p]
    base_url = get_request_base_url(plugin, request)
    site_name = plugin.config.get_value(CONF_SITE_NAME, DEFAULT_SITE_NAME)
    theme_color = plugin.config.get_value(CONF_THEME_COLOR, DEFAULT_THEME_COLOR)

    # If visiting /s or /s/, show the link generator tool
    if len(parts) <= 1:
        html_text = render_link_generator_page(
            site_name=site_name,
            theme_color=theme_color,
            base_url=base_url,
        )
        return web.Response(text=html_text, content_type="text/html")

    if len(parts) < 4:
        raise web.HTTPFound("/")

    media_type = normalize_media_type(parts[1])
    provider_id = parts[2]
    item_id = "/".join(parts[3:])
    autoplay = plugin.config.get_value(CONF_AUTOPLAY, DEFAULT_AUTOPLAY)
    author_template = plugin.config.get_value(CONF_EMBED_AUTHOR_TEMPLATE, DEFAULT_EMBED_AUTHOR_TEMPLATE)
    title_template = plugin.config.get_value(CONF_EMBED_TITLE_TEMPLATE, DEFAULT_EMBED_TITLE_TEMPLATE)
    desc_template = plugin.config.get_value(CONF_EMBED_DESC_TEMPLATE, DEFAULT_EMBED_DESC_TEMPLATE)
    footer_template = plugin.config.get_value(CONF_EMBED_FOOTER_TEMPLATE, DEFAULT_EMBED_FOOTER_TEMPLATE)

    try:
        item = await resolve_media_item(plugin, media_type, provider_id, item_id)
    except Exception as e:
        LOGGER.warning("Error resolving media item %s/%s/%s: %s", media_type, provider_id, item_id, e)
        item = None

    if not item:
        raise web.HTTPFound("/")

    album_name = ""
    item_year = ""
    title = item.name
    artist_name = getattr(item, "artists", [None])[0].name if hasattr(item, "artists") and item.artists else ""
    if not artist_name and hasattr(item, "artist") and item.artist:
        artist_name = item.artist.name
    if hasattr(item, "album") and item.album:
        album_name = item.album.name if hasattr(item.album, "name") else str(item.album)
    if hasattr(item, "year") and item.year:
        item_year = item.year
    image_url = get_image_url(plugin, item, base_url)

    stream_url = f"/stream_guest/{media_type}/{provider_id}/{urllib.parse.quote(item_id)}"
    api_url = f"/api_guest/{media_type}/{provider_id}/{urllib.parse.quote(item_id)}"
    item_duration = item.duration if item and hasattr(item, "duration") and item.duration else 0
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
        duration=item_duration,
        autoplay=autoplay,
        author_template=author_template,
        title_template=title_template,
        desc_template=desc_template,
        footer_template=footer_template,
        album_name=album_name,
        year=item_year,
        provider_name=provider_id,
    )
    return web.Response(text=html_text, content_type="text/html")


async def handle_api_info(plugin: GuestPlayerPlugin, request: web.Request) -> web.Response:
    """Return JSON payload of track(s) for the player."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 4:
        return web.json_response({"error": "Invalid path"}, status=400)

    media_type = normalize_media_type(parts[1])
    provider_id = parts[2]
    item_id = "/".join(parts[3:])

    base_url = get_request_base_url(plugin, request)
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
                valid_pm = None
                if hasattr(t, "provider_mappings") and t.provider_mappings:
                    for pm in t.provider_mappings:
                        if getattr(pm, "available", True) and plugin.mass.get_provider(pm.provider_instance):
                            valid_pm = pm
                            break
                    if not valid_pm:
                        for pm in t.provider_mappings:
                            if plugin.mass.get_provider(pm.provider_instance):
                                valid_pm = pm
                                break

                if not valid_pm:
                    track_prov_inst = getattr(t, "provider", None)
                    if not track_prov_inst or not plugin.mass.get_provider(track_prov_inst):
                        continue

                t_prov = valid_pm.provider_instance if valid_pm else getattr(t, "provider", provider_id)
                t_id = getattr(valid_pm, "provider_item_id", None) or getattr(valid_pm, "item_id", None) if valid_pm else t.item_id
                s_url = f"/stream_guest/track/{t_prov}/{urllib.parse.quote(str(t_id))}"
                if cache_bypass:
                    s_url += f"?v={int(time.time())}"
                tracks_list.append({
                    "id": str(t_id),
                    "provider": t_prov,
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
                # Playlists can contain Tracks or Radio items
                is_radio = getattr(t, "media_type", None) == "radio" or type(t).__name__ == "Radio"
                if is_radio:
                    art_name = "Live Radio"
                    stream_prefix = "radio"
                    dur = 0
                else:
                    stream_prefix = "track"
                    dur = getattr(t, "duration", 0) or 0
                    if hasattr(t, "artists") and t.artists:
                        art_name = t.artists[0].name
                    elif hasattr(t, "artist") and t.artist:
                        art_name = t.artist.name if hasattr(t.artist, "name") else str(t.artist)
                    else:
                        art_name = ""

                # Pick an active streaming provider mapping if available
                pms = list(t.provider_mappings) if hasattr(t, "provider_mappings") and t.provider_mappings else []
                raw_id = str(getattr(t, "item_id", ""))
                
                # Check if raw_id is a URI (e.g. spotify://track/..., ytmusic_free://track/...)
                uri_prov_domain = None
                uri_actual_id = raw_id
                if "://" in raw_id:
                    uri_prov_domain, uri_rest = raw_id.split("://", 1)
                    uri_parts = uri_rest.split("/", 1)
                    uri_actual_id = uri_parts[1] if len(uri_parts) > 1 else uri_parts[0]

                if not pms and not is_radio:
                    if hasattr(t, "item_id") and getattr(t, "provider", None) == "library":
                        try:
                            pms = await plugin.mass.music.tracks.get_provider_mappings(t.item_id, "library")
                        except Exception:
                            pms = []
                    elif uri_prov_domain and uri_actual_id:
                        try:
                            p = plugin.mass.get_provider(uri_prov_domain)
                            if p:
                                lib_track = await plugin.mass.music.tracks.get_by_provider_item_id(uri_actual_id, p.instance_id)
                                if lib_track and lib_track.provider_mappings:
                                    pms = list(lib_track.provider_mappings)
                        except Exception:
                            pass

                valid_pm = None
                for pm in pms:
                    if getattr(pm, "available", True) and plugin.mass.get_provider(pm.provider_instance):
                        valid_pm = pm
                        break
                if not valid_pm:
                    for pm in pms:
                        if plugin.mass.get_provider(pm.provider_instance):
                            valid_pm = pm
                            break

                # If no direct provider mapping, check matching active instances in MA
                target_prov_inst = None
                target_item_id = None

                if valid_pm:
                    target_prov_inst = valid_pm.provider_instance
                    target_item_id = getattr(valid_pm, "provider_item_id", None) or getattr(valid_pm, "item_id", None)
                elif uri_prov_domain:
                    # Find active provider instance matching uri domain (e.g. ytmusic_free, filesystem_local)
                    for p in plugin.mass.providers:
                        if (getattr(p, "domain", None) == uri_prov_domain or getattr(p, "instance_id", None) == uri_prov_domain) and getattr(p, "available", True):
                            target_prov_inst = p.instance_id
                            target_item_id = uri_actual_id
                            break
                elif is_radio:
                    target_prov_inst = getattr(t, "provider", provider_id)
                    target_item_id = t.item_id
                else:
                    track_prov = getattr(t, "provider", None)
                    if track_prov and track_prov not in ("builtin", "library") and plugin.mass.get_provider(track_prov):
                        target_prov_inst = track_prov
                        target_item_id = t.item_id

                # If we cannot resolve to an active, valid streaming provider, skip this unplayable track!
                # Specifically exclude unconfigured/disabled external providers (such as spotify)
                if not target_prov_inst or not target_item_id:
                    continue
                if uri_prov_domain and not any((getattr(p, "domain", None) == uri_prov_domain or getattr(p, "instance_id", None) == uri_prov_domain) and getattr(p, "available", True) for p in plugin.mass.providers):
                    continue

                s_url = f"/stream_guest/{stream_prefix}/{target_prov_inst}/{urllib.parse.quote(str(target_item_id))}"
                if cache_bypass:
                    s_url += f"?v={int(time.time())}"
                tracks_list.append({
                    "id": str(target_item_id),
                    "provider": target_prov_inst,
                    "name": t.name,
                    "artist": art_name,
                    "duration": dur,
                    "media_type": stream_prefix,
                    "image": get_image_url(plugin, t, base_url) if hasattr(t, "image") and t.image else pl_img,
                    "stream_url": s_url,
                })
        elif media_type == "artist":
            tracks_gen = plugin.mass.music.artists.tracks(item_id, provider_id)
            tracks = [t async for t in tracks_gen]
            for t in tracks:
                art_name = t.artists[0].name if t.artists else ""
                pm = next(iter(t.provider_mappings)) if t.provider_mappings else None
                t_prov = pm.provider_instance if pm else provider_id
                t_id = pm.item_id if pm else t.item_id
                s_url = f"/stream_guest/track/{t_prov}/{urllib.parse.quote(str(t_id))}"
                if cache_bypass:
                    s_url += f"?v={int(time.time())}"
                tracks_list.append({
                    "id": str(t_id),
                    "provider": t_prov,
                    "name": t.name,
                    "artist": art_name,
                    "duration": t.duration,
                    "image": get_image_url(plugin, t, base_url),
                    "stream_url": s_url,
                })
        elif media_type == "radio":
            radio = await plugin.mass.music.radio.get(item_id, provider_id)
            pm = next(iter(radio.provider_mappings)) if radio.provider_mappings else None
            r_prov = pm.provider_instance if pm else provider_id
            r_id = pm.item_id if pm else radio.item_id
            s_url = f"/stream_guest/radio/{r_prov}/{urllib.parse.quote(str(r_id))}"
            if cache_bypass:
                s_url += f"?v={int(time.time())}"
            tracks_list.append({
                "id": str(r_id),
                "provider": r_prov,
                "name": radio.name,
                "artist": "Live Radio",
                "duration": 0,
                "image": get_image_url(plugin, radio, base_url),
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
                "id": str(t_id),
                "provider": t_prov,
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


async def handle_stream_audio(plugin: GuestPlayerPlugin, request: web.Request) -> web.StreamResponse:
    """Stream real-time audio."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 4:
        return web.Response(text="Invalid stream URL", status=400)

    media_type = normalize_media_type(parts[1])
    provider_id = parts[2]
    item_id = urllib.parse.unquote("/".join(parts[3:]))
    cache_bypass = plugin.config.get_value(CONF_CACHE_BYPASS, DEFAULT_CACHE_BYPASS)
    return await stream_track_audio(plugin.mass, request, provider_id, item_id, media_type=media_type, cache_bypass=cache_bypass)
