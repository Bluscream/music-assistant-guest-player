"""Audio streaming and transcoding pipeline for Guest Player."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web
from music_assistant.helpers.ffmpeg import get_ffmpeg_stream
from music_assistant_models.enums import ContentType, MediaType
from music_assistant_models.media_items import AudioFormat

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant

LOGGER = logging.getLogger(__name__)


async def stream_track_audio(
    mass: MusicAssistant,
    request: web.Request,
    provider_id: str,
    item_id: str,
    media_type: str = "track",
    cache_bypass: bool = True,
) -> web.StreamResponse | web.Response:
    """Stream real-time transcoded MP3 (192k) directly to client browser."""
    try:
        m_type = MediaType.RADIO if media_type == "radio" else MediaType.TRACK
        if "://" in item_id:
            uri_prov, rest = item_id.split("://", 1)
            uri_parts = rest.split("/", 1)
            uri_item_id = uri_parts[1] if len(uri_parts) > 1 else uri_parts[0]
            # Try all active provider instances matching uri_prov
            for p in mass.providers:
                if (p.domain == uri_prov or p.instance_id == uri_prov) and getattr(p, "available", True):
                    try:
                        stream_details = await p.get_stream_details(uri_item_id, m_type)
                        if stream_details:
                            prov = p
                            item_id = uri_item_id
                            break
                    except Exception:
                        continue
            if not stream_details:
                prov = mass.get_provider(provider_id)
        else:
            prov = mass.get_provider(provider_id)

        if prov and not stream_details:
            try:
                stream_details = await prov.get_stream_details(item_id, m_type)
            except Exception:
                stream_details = None

        if not stream_details:
            if m_type == MediaType.RADIO:
                item = await mass.music.radio.get(item_id, provider_id)
            else:
                item = await mass.music.tracks.get(item_id, provider_id)

            if not item:
                return web.Response(text="Item not found", status=404)

            valid_pm = None
            if item.provider_mappings:
                for pm in item.provider_mappings:
                    if pm.available and mass.get_provider(pm.provider_instance):
                        valid_pm = pm
                        break
                if not valid_pm:
                    for pm in item.provider_mappings:
                        if mass.get_provider(pm.provider_instance):
                            valid_pm = pm
                            break

            if not valid_pm:
                return web.Response(text="No playable streaming provider found for item", status=404)

            target_instance = valid_pm.provider_instance
            target_item_id = valid_pm.item_id

            prov = mass.get_provider(target_instance)
            if not prov:
                return web.Response(text=f"Provider {target_instance} not found", status=404)
            stream_details = await prov.get_stream_details(target_item_id, m_type)

        offset = 0
        if "offset" in request.query:
            try:
                offset = int(float(request.query["offset"]))
            except (ValueError, TypeError):
                offset = 0

        # Ensure seeking flags and duration are present on stream_details
        if stream_details:
            stream_details.allow_seek = True
            stream_details.can_seek = True
            if not stream_details.duration:
                # Fill duration from track item or offset + 300
                stream_details.duration = max(offset + 300, 300)

        pcm_format = AudioFormat(
            content_type=ContentType.PCM_S16LE,
            sample_rate=44100,
            bit_depth=16,
            channels=2,
        )
        audio_stream = mass.streams.audio.get_media_stream(
            stream_details, pcm_format, seek_position=offset
        )

        out_format = AudioFormat(
            content_type=ContentType.MP3,
            sample_rate=44100,
            bit_depth=16,
            channels=2,
            bit_rate=192,
        )

        headers = {
            "Content-Type": "audio/mpeg",
            "Accept-Ranges": "none",
            "Access-Control-Allow-Origin": "*",
        }
        if cache_bypass:
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            })

        response = web.StreamResponse(
            status=200,
            headers=headers,
        )
        await response.prepare(request)

        async for chunk in get_ffmpeg_stream(
            audio_input=audio_stream,
            input_format=pcm_format,
            output_format=out_format,
        ):
            await response.write(chunk)

        await response.write_eof()
        return response
    except Exception as e:
        LOGGER.warning("Stream failed or client disconnected: %s", e)
        return web.Response(text=str(e), status=500)
