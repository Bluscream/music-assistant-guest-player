"""
Guest Player Plugin Provider for Music Assistant.

Allows sharing direct playback links for Tracks, Albums, and Playlists to guests (e.g. m.minopia.de/s/track/<provider>/<item_id>)
with rich Discord / OpenGraph embed cards and a modern web audio player with queue support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohttp import web
from music_assistant.models.plugin import PluginProvider

from .config import get_config_entries as get_config_entries
from .routes import (
    handle_api_info,
    handle_image_guest,
    handle_share_view,
    handle_stream_audio,
)

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

SUPPORTED_FEATURES = set()


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return GuestPlayerPlugin(mass, manifest, config, SUPPORTED_FEATURES)


class GuestPlayerPlugin(PluginProvider):
    """Guest Player plugin provider."""

    _unregister_share_route: Any
    _unregister_stream_route: Any
    _unregister_info_route: Any
    _unregister_image_route: Any

    async def get_config_entries(
        self,
        action: str | None = None,
        values: dict[str, ConfigValueType] | None = None,
    ) -> tuple[ConfigEntry, ...]:
        """Return Config entries to configure this provider instance."""
        return await get_config_entries(self.mass, self.instance_id, action=action, values=values)

    async def loaded_in_mass(self) -> None:
        """Call after the provider has been loaded."""
        async def _guest_dispatcher(request: web.Request) -> web.Response | web.StreamResponse:
            path = request.path
            if path.startswith("/stream_guest/"):
                return await handle_stream_audio(self, request)
            elif path.startswith("/api_guest/"):
                return await handle_api_info(self, request)
            elif path.startswith("/image_guest/"):
                return await handle_image_guest(self, request)
            elif path == "/s" or path.startswith("/s/"):
                return await handle_share_view(self, request)
            return web.Response(status=404, text="Not Found")

        self._unregister_share_route = self.mass.webserver.register_dynamic_route(
            "/s/*", _guest_dispatcher, "*"
        )
        self._unregister_s_exact = self.mass.webserver.register_dynamic_route(
            "/s", _guest_dispatcher, "*"
        )
        self._unregister_s_slash = self.mass.webserver.register_dynamic_route(
            "/s/", _guest_dispatcher, "*"
        )
        self._unregister_stream_route = self.mass.webserver.register_dynamic_route(
            "/stream_guest/*", _guest_dispatcher, "*"
        )
        self._unregister_info_route = self.mass.webserver.register_dynamic_route(
            "/api_guest/*", _guest_dispatcher, "*"
        )
        self._unregister_image_route = self.mass.webserver.register_dynamic_route(
            "/image_guest/*", _guest_dispatcher, "*"
        )
        self.logger.info("Guest Player routes registered: /s/*, /s, /s/, /stream_guest/*, /api_guest/*, /image_guest/*")
        self.mass.loop.create_task(self._ensure_all_tracks_playlist())

    async def _ensure_all_tracks_playlist(self) -> None:
        """Create or update the 'All Library Tracks' playlist with all library tracks."""
        playlist_name = "All Library Tracks"
        try:
            target_pl = None
            async for pl in self.mass.music.playlists.iter_library_items():
                if pl.name == playlist_name:
                    target_pl = pl
                    break

            if not target_pl:
                self.logger.info("Creating '%s' playlist...", playlist_name)
                target_pl = await self.mass.music.playlists.create_playlist(
                    name=playlist_name,
                    provider_instance_or_domain="builtin",
                )
            else:
                # If playlist already contains tracks, skip re-populating on every restart
                existing = [t async for t in self.mass.music.playlists.tracks(target_pl.item_id, target_pl.provider)]
                if existing:
                    self.logger.debug("Playlist '%s' already populated (%d tracks), skipping startup sync.", playlist_name, len(existing))
                    return

            # Collect all library track URIs
            uris = []
            async for track in self.mass.music.tracks.iter_library_items():
                uris.append(track.uri)

            self.logger.info("Syncing %d library tracks into '%s' playlist...", len(uris), playlist_name)
            if uris:
                # Add tracks in batches of 200
                for i in range(0, len(uris), 200):
                    batch = uris[i : i + 200]
                    await self.mass.music.playlists.add_playlist_tracks(target_pl.item_id, batch)
            self.logger.info("Successfully populated '%s' playlist with %d tracks.", playlist_name, len(uris))
        except Exception as e:
            self.logger.warning("Failed to create/populate '%s': %s", playlist_name, e)

    async def unload(self, is_removed: bool = False) -> None:
        """Handle unload/close of the provider."""
        if hasattr(self, "_unregister_share_route") and self._unregister_share_route:
            self._unregister_share_route()
        if hasattr(self, "_unregister_s_exact") and self._unregister_s_exact:
            self._unregister_s_exact()
        if hasattr(self, "_unregister_s_slash") and self._unregister_s_slash:
            self._unregister_s_slash()
        if hasattr(self, "_unregister_stream_route") and self._unregister_stream_route:
            self._unregister_stream_route()
        if hasattr(self, "_unregister_info_route") and self._unregister_info_route:
            self._unregister_info_route()
        if hasattr(self, "_unregister_image_route") and self._unregister_image_route:
            self._unregister_image_route()
        self.logger.info("Guest Player routes unregistered.")
