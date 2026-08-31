"""HTML & OpenGraph embed template generator for Guest Share Player."""

from __future__ import annotations

import html
import json


def render_player_page(
    media_type: str,
    title: str,
    artist_name: str,
    image_url: str,
    stream_url: str,
    api_url: str,
    page_url: str,
    site_name: str,
    theme_color: str,
    duration: int = 0,
) -> str:
    """Generate modern full-width Music Assistant styled player matching the official UI."""
    # Build clean Discord description (meta tags do not parse markdown like **)
    if media_type == "track":
        dur_str = f" • {duration // 60}:{duration % 60:02d}" if duration else ""
        if artist_name:
            description = f"🎵 Track by {artist_name}{dur_str}\n▶️ Click above to play live"
        else:
            description = f"🎵 Track{dur_str}\n▶️ Click above to play live"
    elif media_type == "playlist":
        description = f"📋 Playlist • Stream on {site_name}\n▶️ Click above to open and listen"
    elif media_type == "album":
        if artist_name:
            description = f"💿 Album by {artist_name}\n▶️ Click above to listen"
        else:
            description = f"💿 Album • Stream on {site_name}\n▶️ Click above to listen"
    else:
        description = f"Listen on {site_name}"

    escaped_title = html.escape(title)
    escaped_desc = html.escape(description)
    escaped_site_name = html.escape(site_name)
    # Ensure image_url is absolute so Discord proxy can fetch it
    full_img_url = image_url if image_url.startswith("http") else f"{page_url.split('/s/')[0]}{image_url}"
    escaped_img = html.escape(full_img_url)
    escaped_artist = html.escape(artist_name or site_name)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{escaped_title} - {escaped_site_name}</title>
  
  <!-- Open Graph / Facebook / Discord -->
  <meta property="og:type" content="music.song">
  <meta property="og:site_name" content="{escaped_site_name}">
  <meta property="og:title" content="{escaped_title}">
  <meta property="og:description" content="{escaped_desc}">
  <meta property="og:image" content="{escaped_img}">
  <meta property="og:url" content="{page_url}">
  <meta name="theme-color" content="{theme_color}">

  <!-- Twitter Card: 'summary' forces Discord to display compact right-side thumbnail instead of huge stretched box -->
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{escaped_title}">
  <meta name="twitter:description" content="{escaped_desc}">
  <meta name="twitter:image" content="{escaped_img}">

  <!-- Fonts & Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">

  <style>
    :root {{
      --bg-color: #1a1714;
      --panel-bg: rgba(28, 25, 23, 0.7);
      --accent: {theme_color};
      --text-main: #f8fafc;
      --text-muted: #a8a29e;
      --border: rgba(255, 255, 255, 0.08);
      --btn-active: rgba(255, 255, 255, 0.12);
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      -webkit-tap-highlight-color: transparent;
    }}
    html, body {{
      width: 100%;
      height: 100%;
      background-color: var(--bg-color);
      color: var(--text-main);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    /* Dynamic adaptive blurred background */
    .backdrop {{
      position: fixed;
      inset: -20%;
      background-image: url('{escaped_img}');
      background-size: cover;
      background-position: center;
      filter: blur(70px) brightness(0.2) saturate(1.6);
      z-index: 0;
      transition: background-image 0.5s ease-in-out;
      pointer-events: none;
    }}
    /* Top Bar */
    .top-bar {{
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 32px;
      border-bottom: 1px solid var(--border);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 1.1rem;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}
    .brand i {{
      color: var(--accent);
    }}
    .media-badge {{
      font-size: 0.75rem;
      background: rgba(255, 255, 255, 0.1);
      padding: 4px 10px;
      border-radius: 12px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--accent);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    /* Main Layout Area */
    .main-content {{
      position: relative;
      z-index: 1;
      flex: 1;
      display: flex;
      padding: 32px 48px 16px;
      gap: 48px;
      overflow: hidden;
    }}
    /* Left: Now Playing Stage */
    .now-playing-panel {{
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      max-width: 50%;
    }}
    .cover-container {{
      width: min(380px, 60vh);
      aspect-ratio: 1/1;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
      background: #111;
      margin-bottom: 24px;
      border: 1px solid var(--border);
    }}
    .cover-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
    }}
    .now-playing-meta {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-width: 80%;
    }}
    .now-title {{
      font-size: 1.6rem;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .now-artist {{
      font-size: 1.1rem;
      color: var(--text-muted);
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    /* Right: Queue / Tracklist Panel */
    .tracklist-panel {{
      flex: 1;
      display: flex;
      flex-direction: column;
      background: var(--panel-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-radius: 16px;
      border: 1px solid var(--border);
      padding: 20px;
      overflow: hidden;
    }}
    .tracklist-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .tracklist-scroll {{
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding-right: 4px;
    }}
    .track-row {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 10px 14px;
      border-radius: 10px;
      cursor: pointer;
      transition: background 0.15s ease;
    }}
    .track-row:hover {{
      background: rgba(255, 255, 255, 0.06);
    }}
    .track-row.active {{
      background: color-mix(in srgb, var(--accent) 15%, transparent);
      border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
    }}
    .track-row-art {{
      width: 44px;
      height: 44px;
      border-radius: 6px;
      object-fit: cover;
      background: #222;
      flex-shrink: 0;
    }}
    .track-row-info {{
      flex: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .track-row-title {{
      font-size: 0.95rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .track-row.active .track-row-title {{
      color: var(--accent);
    }}
    .track-row-artist {{
      font-size: 0.8rem;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .track-row-dur {{
      font-size: 0.85rem;
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
    }}
    /* Bottom Player Bar */
    .player-bar {{
      position: relative;
      z-index: 2;
      background: rgba(18, 16, 14, 0.9);
      backdrop-filter: blur(30px);
      -webkit-backdrop-filter: blur(30px);
      border-top: 1px solid var(--border);
      padding: 14px 32px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .scrubber-row {{
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
    }}
    .time-txt {{
      font-size: 0.8rem;
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
      min-width: 38px;
    }}
    .progress-bar-wrap {{
      flex: 1;
      height: 6px;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      cursor: pointer;
      position: relative;
    }}
    .progress-bar-fill {{
      height: 100%;
      width: 0%;
      background: var(--accent);
      border-radius: 8px;
      position: relative;
    }}
    .controls-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .player-side {{
      display: flex;
      align-items: center;
      gap: 12px;
      width: 25%;
    }}
    .center-controls {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 16px;
      flex: 1;
    }}
    .btn-ctrl {{
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 1.1rem;
      cursor: pointer;
      padding: 8px 12px;
      border-radius: 50%;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .btn-ctrl:hover {{
      color: #fff;
      transform: scale(1.1);
    }}
    .btn-main-play {{
      background: #fff;
      color: #000;
      font-size: 1.3rem;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      box-shadow: 0 4px 16px rgba(255, 255, 255, 0.2);
    }}
    .btn-main-play:hover {{
      background: var(--accent);
      color: #fff;
      transform: scale(1.08);
      box-shadow: 0 6px 20px rgba(255, 51, 102, 0.4);
    }}
    .volume-ctrl {{
      display: flex;
      align-items: center;
      gap: 10px;
      width: 25%;
      justify-content: flex-end;
    }}
    .vol-slider {{
      accent-color: var(--accent);
      cursor: pointer;
      width: 90px;
    }}
    /* Scrollbar */
    .tracklist-scroll::-webkit-scrollbar {{
      width: 5px;
    }}
    .tracklist-scroll::-webkit-scrollbar-thumb {{
      background: rgba(255, 255, 255, 0.2);
      border-radius: 5px;
    }}
    @media (max-width: 900px) {{
      .main-content {{
        flex-direction: column;
        padding: 16px;
        gap: 16px;
        overflow-y: auto;
      }}
      .now-playing-panel {{
        max-width: 100%;
      }}
      .cover-container {{
        width: min(240px, 40vh);
        margin-bottom: 12px;
      }}
      .player-side, .volume-ctrl {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="backdrop" id="backdrop"></div>

  <div class="top-bar">
    <div class="brand">
      <i class="fa-solid fa-compact-disc fa-spin" style="--fa-animation-duration: 6s;"></i>
      <span>{escaped_site_name}</span>
    </div>
    <span class="media-badge">{media_type.upper()}</span>
  </div>

  <div class="main-content">
    <div class="now-playing-panel">
      <div class="cover-container">
        <img src="{escaped_img}" alt="" class="cover-img" id="artImg">
      </div>
      <div class="now-playing-meta">
        <div class="now-title" id="trackTitle">{escaped_title}</div>
        <div class="now-artist" id="trackArtist">{escaped_artist}</div>
      </div>
    </div>

    <div class="tracklist-panel" id="tracklistPanel">
      <div class="tracklist-header">
        <span>Tracks / Queue</span>
        <span id="trackCount">0 tracks</span>
      </div>
      <div class="tracklist-scroll" id="trackList"></div>
    </div>
  </div>

  <div class="player-bar">
    <div class="scrubber-row">
      <span class="time-txt" id="currentTime">0:00</span>
      <div class="progress-bar-wrap" id="progressBarWrap">
        <div class="progress-bar-fill" id="progressBar"></div>
      </div>
      <span class="time-txt" id="duration">0:00</span>
    </div>

    <div class="controls-row">
      <div class="player-side">
        <div style="color: var(--text-muted); font-size: 0.75rem; display: flex; align-items: center; gap: 5px;">
          <i class="fa-solid fa-bolt" style="color: var(--accent); font-size: 0.7rem;"></i>
          <span>Powered by <a href="https://music-assistant.io" target="_blank" rel="noopener noreferrer" style="color: var(--text-muted); text-decoration: underline; transition: color 0.2s ease;" onmouseover="this.style.color='var(--text-main)'" onmouseout="this.style.color='var(--text-muted)'"><strong>Music Assistant</strong></a> and <a href="https://github.com/Bluscream/music-assistant-guest-share-player" target="_blank" rel="noopener noreferrer" style="color: var(--text-muted); text-decoration: underline; transition: color 0.2s ease;" onmouseover="this.style.color='var(--text-main)'" onmouseout="this.style.color='var(--text-muted)'"><strong>Guest Player</strong></a></span>
        </div>
      </div>
      <div class="center-controls">
        <button class="btn-ctrl" id="prevBtn" title="Previous"><i class="fa-solid fa-backward-step"></i></button>
        <button class="btn-ctrl btn-main-play" id="playBtn" title="Play/Pause"><i class="fa-solid fa-play" id="playIcon"></i></button>
        <button class="btn-ctrl" id="nextBtn" title="Next"><i class="fa-solid fa-forward-step"></i></button>
        <button class="btn-ctrl" id="loopBtn" title="Loop"><i class="fa-solid fa-repeat"></i></button>
      </div>
      <div class="volume-ctrl">
        <i class="fa-solid fa-volume-high" style="color: var(--text-muted); font-size: 0.9rem;"></i>
        <input type="range" class="vol-slider" id="volSlider" min="0" max="1" step="0.01" value="1">
      </div>
    </div>
  </div>

  <audio id="audioElement" preload="auto"></audio>

  <script>
    const audio = document.getElementById('audioElement');
    const playBtn = document.getElementById('playBtn');
    const playIcon = document.getElementById('playIcon');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const loopBtn = document.getElementById('loopBtn');
    const volSlider = document.getElementById('volSlider');
    const progressBar = document.getElementById('progressBar');
    const progressContainer = document.getElementById('progressBarWrap');
    const currentTimeEl = document.getElementById('currentTime');
    const durationEl = document.getElementById('duration');
    const trackTitleEl = document.getElementById('trackTitle');
    const trackArtistEl = document.getElementById('trackArtist');
    const artImg = document.getElementById('artImg');
    const backdrop = document.getElementById('backdrop');
    const trackListEl = document.getElementById('trackList');
    const trackCountEl = document.getElementById('trackCount');

    let playlist = [];
    let currentIndex = 0;
    let isLooping = false;
    let seekOffset = 0;

    const initialItem = {{
      name: {json.dumps(title)},
      artist: {json.dumps(artist_name)},
      image: {json.dumps(image_url)},
      media_type: {json.dumps(media_type)},
      stream_url: {json.dumps(stream_url)}
    }};

    function formatTime(secs) {{
      if (!isFinite(secs) || isNaN(secs) || secs < 0) return '0:00';
      const m = Math.floor(secs / 60);
      const s = Math.floor(secs % 60);
      return `${{m}}:${{s < 10 ? '0' : ''}}${{s}}`;
    }}

    function getTrackDuration() {{
      const currentTrack = playlist[currentIndex];
      if (currentTrack && currentTrack.duration && isFinite(currentTrack.duration)) {{
        return currentTrack.duration;
      }}
      if (audio.duration && isFinite(audio.duration)) {{
        return audio.duration;
      }}
      return 0;
    }}

    async function loadData() {{
      try {{
        const res = await fetch('{api_url}');
        const data = await res.json();
        if (data.tracks && data.tracks.length > 0) {{
          playlist = data.tracks;
          trackCountEl.textContent = `${{playlist.length}} track${{playlist.length === 1 ? '' : 's'}}`;
          renderTracklist();
          setTrack(0, false);
        }} else {{
          playlist = [initialItem];
          trackCountEl.textContent = '1 track';
          renderTracklist();
          setTrack(0, false);
        }}
      }} catch (e) {{
        playlist = [initialItem];
        trackCountEl.textContent = '1 track';
        renderTracklist();
        setTrack(0, false);
      }}
    }}

    function renderTracklist() {{
      trackListEl.innerHTML = '';
      playlist.forEach((track, idx) => {{
        const row = document.createElement('div');
        row.className = `track-row ${{idx === currentIndex ? 'active' : ''}}`;
        const imgPath = track.image || '{escaped_img}';
        row.innerHTML = `
          <img src="${{imgPath}}" class="track-row-art" alt="">
          <div class="track-row-info">
            <span class="track-row-title">${{track.name}}</span>
            <span class="track-row-artist">${{track.artist || '{escaped_site_name}'}}</span>
          </div>
          <span class="track-row-dur">${{formatTime(track.duration || 0)}}</span>
        `;
        row.onclick = () => setTrack(idx, true);
        trackListEl.appendChild(row);
      }});
    }}

    function setTrack(index, playImmediately = true, offsetSeconds = 0) {{
      if (index < 0 || index >= playlist.length) return;
      currentIndex = index;
      seekOffset = offsetSeconds;
      const track = playlist[index];
      trackTitleEl.textContent = track.name;
      trackArtistEl.textContent = track.artist || '{escaped_site_name}';
      
      const imgPath = track.image || '{escaped_img}';
      artImg.src = imgPath;
      backdrop.style.backgroundImage = `url('${{imgPath}}')`;
      
      let baseStreamUrl = track.stream_url.startsWith('http') ? track.stream_url : window.location.origin + track.stream_url;
      const joinChar = baseStreamUrl.includes('?') ? '&' : '?';
      const streamUrl = `${{baseStreamUrl}}${{joinChar}}offset=${{Math.floor(offsetSeconds)}}&_t=${{Date.now()}}`;
      
      audio.src = streamUrl;
      audio.load();

      const dur = getTrackDuration();
      durationEl.textContent = formatTime(dur);
      const startPct = dur > 0 ? Math.min(100, Math.max(0, (offsetSeconds / dur) * 100)) : 0;
      progressBar.style.width = startPct + '%';
      currentTimeEl.textContent = formatTime(offsetSeconds);
      renderTracklist();

      if ('mediaSession' in navigator) {{
        navigator.mediaSession.metadata = new MediaMetadata({{
          title: track.name,
          artist: track.artist,
          artwork: [{{ src: imgPath }}]
        }});
      }}

      if (playImmediately) {{
        audio.play().catch(e => console.log('Autoplay prevent:', e));
      }}
    }}

    playBtn.onclick = () => {{
      if (!audio.src || audio.src === '' || audio.src === window.location.href) {{
        setTrack(currentIndex, true, seekOffset);
        return;
      }}
      if (audio.paused) {{
        audio.play().catch(e => console.log('Playback error:', e));
      }} else {{
        audio.pause();
      }}
    }};

    audio.onplay = () => {{
      playIcon.className = 'fa-solid fa-pause';
    }};

    audio.onpause = () => {{
      playIcon.className = 'fa-solid fa-play';
    }};

    audio.ontimeupdate = () => {{
      const dur = getTrackDuration();
      const currentPos = seekOffset + (isFinite(audio.currentTime) ? audio.currentTime : 0);
      if (dur > 0) {{
        const pct = Math.min(100, Math.max(0, (currentPos / dur) * 100));
        progressBar.style.width = pct + '%';
        durationEl.textContent = formatTime(dur);
      }}
      currentTimeEl.textContent = formatTime(currentPos);
    }};

    audio.onloadedmetadata = () => {{
      const dur = getTrackDuration();
      durationEl.textContent = formatTime(dur);
    }};

    audio.onended = () => {{
      if (isLooping) {{
        setTrack(currentIndex, true, 0);
      }} else if (currentIndex + 1 < playlist.length) {{
        setTrack(currentIndex + 1, true, 0);
      }} else {{
        playIcon.className = 'fa-solid fa-play';
      }}
    }};

    prevBtn.onclick = () => {{
      const currentPos = seekOffset + (isFinite(audio.currentTime) ? audio.currentTime : 0);
      if (currentPos > 3) {{
        setTrack(currentIndex, !audio.paused, 0);
      }} else if (currentIndex > 0) {{
        setTrack(currentIndex - 1, true, 0);
      }}
    }};

    nextBtn.onclick = () => {{
      if (currentIndex + 1 < playlist.length) {{
        setTrack(currentIndex + 1, true, 0);
      }}
    }};

    loopBtn.onclick = () => {{
      isLooping = !isLooping;
      loopBtn.style.color = isLooping ? 'var(--accent)' : 'var(--text-muted)';
    }};

    volSlider.oninput = (e) => {{
      audio.volume = e.target.value;
    }};

    progressContainer.onclick = (e) => {{
      const dur = getTrackDuration();
      if (!dur || dur <= 0) return;
      const rect = progressContainer.getBoundingClientRect();
      const pos = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
      const targetSecs = pos * dur;
      const wasPlaying = !audio.paused;
      setTrack(currentIndex, wasPlaying, targetSecs);
    }};

    loadData();
  </script>
</body>
</html>
"""
