"""Route handlers for Guest Player."""

from __future__ import annotations

import logging
import re
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
    render_not_found_page,
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


_IMAGE_CACHE: dict[tuple[str, str], bytes] = {}


async def handle_image_guest(plugin: GuestPlayerPlugin, request: web.Request) -> web.Response:
    """Serve image for guest player with in-memory caching."""
    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 3:
        return web.Response(status=400, text="Invalid image path")

    provider = parts[1]
    path = urllib.parse.unquote("/".join(parts[2:]))
    cache_key = (provider, path)

    if cache_key in _IMAGE_CACHE:
        return web.Response(
            body=_IMAGE_CACHE[cache_key],
            content_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    try:
        data = await plugin.mass.metadata.get_thumbnail(path=path, provider=provider)
        if len(_IMAGE_CACHE) > 500:
            # Evict oldest entries
            for _ in range(50):
                _IMAGE_CACHE.pop(next(iter(_IMAGE_CACHE)), None)
        _IMAGE_CACHE[cache_key] = data
        return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        LOGGER.debug("Serving placeholder for missing guest image %s: %s", path, e)
        theme_color = plugin.config.get_value(CONF_THEME_COLOR, DEFAULT_THEME_COLOR)
        svg_placeholder = render_svg_placeholder(theme_color)
        return web.Response(text=svg_placeholder, content_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


def get_canonical_provider_mapping(item: Any) -> Any:
    """Find the most persistent provider mapping (e.g. filesystem_local or ytmusic_free) on a media item."""
    if not item or not hasattr(item, "provider_mappings") or not item.provider_mappings:
        return None

    # Priority 1: Local filesystem providers (permanent disk paths)
    for pm in item.provider_mappings:
        if getattr(pm, "available", True) and getattr(pm, "provider_domain", "").startswith("filesystem"):
            return pm

    # Priority 2: Streaming / cloud providers (non-library and non-builtin)
    for pm in item.provider_mappings:
        domain = getattr(pm, "provider_domain", "")
        instance = getattr(pm, "provider_instance", "")
        if getattr(pm, "available", True) and domain not in ("library", "builtin") and instance not in ("library", "builtin"):
            return pm

    # Priority 3: Fallback to any non-library instance mapping
    for pm in item.provider_mappings:
        instance = getattr(pm, "provider_instance", "")
        if instance not in ("library", "builtin"):
            return pm

    return None


async def resolve_canonical_url(plugin: GuestPlayerPlugin, raw_url: str, base_url: str) -> str | None:
    """Parse and resolve any raw URL or URI to its permanent guest player URL."""
    raw = raw_url.strip()
    if not raw:
        return None

    # Handle hash format e.g. https://music.minopia.de/#/tracks/2429 or #/playlists/280
    match_hash = re.search(r"#/?(tracks|albums|playlists|artists|radios|track|album|playlist|artist|radio)/(\w+)/?(.+)?", raw, re.I)
    if match_hash:
        m_type = normalize_media_type(match_hash.group(1))
        p_id = match_hash.group(2)
        i_id = match_hash.group(3) or ""
        if not i_id:
            i_id = p_id
            p_id = "library"
    else:
        # Handle guest player URL /s/track/library/2429 or /s/track/filesystem_local--.../...
        match_s = re.search(r"/s/(tracks|albums|playlists|artists|radios|track|album|playlist|artist|radio)/([^/]+)/(.+)", raw, re.I)
        if match_s:
            m_type = normalize_media_type(match_s.group(1))
            p_id = match_s.group(2)
            i_id = urllib.parse.unquote(match_s.group(3))
        else:
            # Handle URI scheme e.g. library://track/2429 or ytmusic_free://track/VkXMXcZu_UI
            match_uri = re.match(r"(\w+)(?:--\w+)?://(track|album|playlist|artist|radio)/(.+)", raw, re.I)
            if match_uri:
                p_id = match_uri.group(1)
                m_type = normalize_media_type(match_uri.group(2))
                i_id = match_uri.group(3)
            else:
                return None

    try:
        item = await resolve_media_item(plugin, m_type, p_id, i_id)
        if item:
            canonical_pm = get_canonical_provider_mapping(item)
            if canonical_pm:
                c_prov = canonical_pm.provider_instance
                c_id = getattr(canonical_pm, "provider_item_id", None) or getattr(canonical_pm, "item_id", None)
                if c_prov and c_id and c_prov != "library":
                    return f"{base_url}/s/{m_type}/{c_prov}/{urllib.parse.quote(str(c_id), safe='')}"
            return f"{base_url}/s/{m_type}/{p_id}/{urllib.parse.quote(str(i_id), safe='')}"
    except Exception as e:
        LOGGER.debug("Could not resolve canonical URL for %s: %s", raw, e)

    return None


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
        html_404 = render_not_found_page(
            site_name=site_name,
            theme_color=theme_color,
            base_url=base_url,
            media_type=media_type,
            provider_id=provider_id,
            item_id=item_id,
        )
        return web.Response(text=html_404, status=404, content_type="text/html")

    # If accessed via transient library ID, redirect to canonical permanent URL
    if provider_id == "library":
        canonical_pm = get_canonical_provider_mapping(item)
        if canonical_pm:
            c_prov = canonical_pm.provider_instance
            c_id = getattr(canonical_pm, "provider_item_id", None) or getattr(canonical_pm, "item_id", None)
            if c_prov and c_id and c_prov != "library":
                canonical_path = f"/s/{media_type}/{c_prov}/{urllib.parse.quote(str(c_id), safe='')}"
                query_str = f"?{request.query_string}" if request.query_string else ""
                raise web.HTTPMovedPermanently(f"{canonical_path}{query_str}")

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

    track_count = 1 if media_type in ("track", "radio") else getattr(item, "tracks_count", getattr(item, "total_tracks", None))

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
        track_count=track_count,
    )
    return web.Response(text=html_text, content_type="text/html")


async def handle_api_info(plugin: GuestPlayerPlugin, request: web.Request) -> web.Response:
    """Return JSON payload of track(s) for the player."""
    if request.path.rstrip("/") == "/api_guest/resolve_url":
        raw_url = request.query.get("url", "").strip()
        if not raw_url:
            return web.json_response({"error": "Missing url parameter"}, status=400)
        base_url = get_request_base_url(plugin, request)
        canonical = await resolve_canonical_url(plugin, raw_url, base_url)
        return web.json_response({"canonical_url": canonical}, headers={"Access-Control-Allow-Origin": "*"})

    parts = [p for p in request.path.split("/") if p]
    if len(parts) < 4:
        return web.json_response({"error": "Invalid path"}, status=400)

    media_type = normalize_media_type(parts[1])
    provider_id = parts[2]
    item_id = "/".join(parts[3:])

    base_url = get_request_base_url(plugin, request)
    cache_bypass = plugin.config.get_value(CONF_CACHE_BYPASS, DEFAULT_CACHE_BYPASS)
    tracks_list = []

    # Pre-index active providers and domains for O(1) lookup
    active_instances = {
        p.instance_id: p for p in plugin.mass.providers if getattr(p, "available", True) and getattr(p, "instance_id", None)
    }
    active_domains = {}
    for p in plugin.mass.providers:
        if getattr(p, "available", True) and getattr(p, "domain", None):
            active_domains.setdefault(p.domain, []).append(p)

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
                        if getattr(pm, "available", True) and pm.provider_instance in active_instances:
                            valid_pm = pm
                            break
                    if not valid_pm:
                        for pm in t.provider_mappings:
                            if pm.provider_instance in active_instances:
                                valid_pm = pm
                                break

                if not valid_pm:
                    track_prov_inst = getattr(t, "provider", None)
                    if not track_prov_inst or track_prov_inst not in active_instances:
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
                        p_matches = active_domains.get(uri_prov_domain) or ([active_instances[uri_prov_domain]] if uri_prov_domain in active_instances else [])
                        if p_matches:
                            try:
                                lib_track = await plugin.mass.music.tracks.get_by_provider_item_id(uri_actual_id, p_matches[0].instance_id)
                                if lib_track and lib_track.provider_mappings:
                                    pms = list(lib_track.provider_mappings)
                            except Exception:
                                pass

                valid_pm = None
                for pm in pms:
                    if getattr(pm, "available", True) and pm.provider_instance in active_instances:
                        valid_pm = pm
                        break
                if not valid_pm:
                    for pm in pms:
                        if pm.provider_instance in active_instances:
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
                    dom_provs = active_domains.get(uri_prov_domain)
                    if dom_provs:
                        target_prov_inst = dom_provs[0].instance_id
                        target_item_id = uri_actual_id
                    elif uri_prov_domain in active_instances:
                        target_prov_inst = uri_prov_domain
                        target_item_id = uri_actual_id
                elif is_radio:
                    target_prov_inst = getattr(t, "provider", provider_id)
                    target_item_id = t.item_id
                else:
                    track_prov = getattr(t, "provider", None)
                    if track_prov and track_prov not in ("builtin", "library") and track_prov in active_instances:
                        target_prov_inst = track_prov
                        target_item_id = t.item_id

                # If we cannot resolve to an active, valid streaming provider, skip this unplayable track!
                if not target_prov_inst or not target_item_id:
                    continue
                if uri_prov_domain and uri_prov_domain not in active_domains and uri_prov_domain not in active_instances:
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
