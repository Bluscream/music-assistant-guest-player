"""Audio streaming and transcoding pipeline for Guest Share Player."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web

from music_assistant_models.enums import ContentType, MediaType
from music_assistant_models.media_items import AudioFormat
from music_assistant.helpers.ffmpeg import get_ffmpeg_stream

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant

LOGGER = logging.getLogger(__name__)


async def stream_track_audio(
    mass: MusicAssistant,
    request: web.Request,
    provider_id: str,
    item_id: str,
    cache_bypass: bool = True,
) -> web.StreamResponse | web.Response:
    """Stream real-time transcoded MP3 (192k) directly to client browser."""
    try:
        prov = mass.get_provider(provider_id)
        if prov:
            try:
                stream_details = await prov.get_stream_details(item_id, MediaType.TRACK)
            except Exception:
                stream_details = None
        else:
            stream_details = None

        if not stream_details:
            track = await mass.music.tracks.get(item_id, provider_id)
            if not track:
                return web.Response(text="Track not found", status=404)

            pm = next(iter(track.provider_mappings)) if track.provider_mappings else None
            target_instance = pm.provider_instance if pm else provider_id
            target_item_id = pm.item_id if pm else item_id

            prov = mass.get_provider(target_instance)
            stream_details = await prov.get_stream_details(target_item_id, MediaType.TRACK)

        offset = 0
        if "offset" in request.query:
            try:
                offset = int(float(request.query["offset"]))
            except (ValueError, TypeError):
                offset = 0

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
