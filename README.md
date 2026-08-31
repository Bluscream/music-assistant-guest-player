# Music Assistant — Guest Share Player Plugin

A modern, standalone web player and sharing companion for [Music Assistant](https://music-assistant.io).

Generate beautiful, embeddable guest share links for any track, album, or playlist with real-time MP3 transcoding, dynamic Discord/OpenGraph metadata cards, full dual-pane UI, cover art resolution, and scrubber seeking.

---

## Features

- **Zero-Authentication Guest Sharing**: Share direct playback links (`/s/<track|album|playlist>/<provider>/<id>`) with friends without exposing internal admin credentials.
- **Modern Full-Width Interface**: Dual-panel design with album artwork stage, dynamic blurred backdrop, scrollable queue/tracklist, volume controls, and transport controls.
- **Interactive Scrubber Seeking**: Seek to any timestamp across the entire track with real-time FFmpeg offset streaming.
- **Automatic Fallback Artwork**: Generates sleek dark-mode vector SVG vinyl artwork for tracks without embedded covers.
- **Discord & Social Previews**: Dynamic OpenGraph & Twitter card meta tags for rich playable embeds on Discord and social platforms.
- **Real-Time On-The-Fly Transcoding**: Direct MP3 (192kbps) stream pipeline powered by Music Assistant's audio engine.

---

## Screenshots

<details>
<summary>📸 Click to expand screenshots</summary>

<br>

| Desktop Guest Player (Now Playing & Queue) |
|:---:|
| [![Guest Share Player Interface](https://i.imgur.com/5QRK3ba.png)](https://i.imgur.com/5QRK3ba.png) |

</details>

---

## Installation

### Unraid / NAS (Docker)

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/Bluscream/music-assistant-guest-share-player/main/scripts/install_provider.sh)"
```

### Home Assistant Add-on

> **Requires the "Advanced SSH & Web Terminal" community add-on** (Protection mode OFF).

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/Bluscream/music-assistant-guest-share-player/main/scripts/install_provider.sh)"
```

---

## Usage

Once installed and enabled in **Settings ➔ Providers ➔ Guest Share Player**:

- **Track Links**: `https://<your-host>/s/track/<provider>/<id>` (e.g. `https://music.example.com/s/track/library/2424`)
- **Playlist Links**: `https://<your-host>/s/playlist/<provider>/<id>` (e.g. `https://music.example.com/s/playlist/library/278`)
- **Album Links**: `https://<your-host>/s/album/<provider>/<id>`

---

## Configuration

| Setting | Default | Description |
|---|---|---|
| `Public Base URL` | `https://m.minopia.de` | The public URL where your player is reached. Used for OpenGraph / Discord embed links. |
| `Site / Service Name` | `Music Assistant` | Brand name displayed in header, page titles, and embeds. |
| `Theme Accent Color` | `#FF3366` | Custom hex accent color for playback controls, active tracks, and progress bars. |

---

## License

MIT License. Powered by [Music Assistant](https://music-assistant.io).
