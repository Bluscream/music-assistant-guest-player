"""HTML & OpenGraph embed template generator for Guest Player."""

from __future__ import annotations

import html
import json
from typing import Any

COMMON_FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">"""

COMMON_FONTS_ICONS = f"""{COMMON_FONTS}<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">"""


def get_base_css(theme_color: str, panel_bg: str = "rgba(28, 25, 23, 0.7)", border: str = "rgba(255, 255, 255, 0.08)") -> str:
    """Return minified base theme CSS variables and global typography reset."""
    return f":root{{--bg-color:#1a1714;--panel-bg:{panel_bg};--accent:{theme_color};--text-main:#f8fafc;--text-muted:#a8a29e;--border:{border};--btn-active:rgba(255,255,255,0.12);}}*{{box-sizing:border-box;margin:0;padding:0;font-family:'Outfit',-apple-system,BlinkMacSystemFont,sans-serif;-webkit-tap-highlight-color:transparent;}}"


def render_svg_placeholder(theme_color: str) -> str:
    """Render minified fallback SVG artwork placeholder for tracks without cover art."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">'
        f'<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2a2523"/><stop offset="100%" stop-color="#141210"/></linearGradient></defs>'
        f'<rect width="500" height="500" rx="20" fill="url(#g)"/>'
        f'<circle cx="250" cy="250" r="110" fill="none" stroke="{theme_color}" stroke-width="6" opacity="0.4"/>'
        f'<circle cx="250" cy="250" r="40" fill="{theme_color}" opacity="0.6"/>'
        f'<path d="M225 180v140a35 35 0 1 0 25 33.5V230l60-15v75a35 35 0 1 0 25 33.5V170l-110 25z" fill="#f8fafc" opacity="0.85"/>'
        f'</svg>'
    )


def format_embed_line(tmpl: str, context: dict[str, Any], default_val: str = "") -> str:
    """Format an embed template string safely using context variables."""
    if not tmpl:
        return default_val
    try:
        return tmpl.format(**context)
    except Exception:
        return default_val


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
    autoplay: bool = False,
    author_template: str = "{site_name}",
    title_template: str = "{title}",
    desc_template: str = "🎵 {media_type_label} by {artist}{duration_str}",
    footer_template: str = "",
    album_name: str = "",
    year: int | str = "",
    provider_name: str = "",
) -> str:
    """Generate modern full-width Music Assistant styled player matching the official UI."""
    media_type_map = {
        "track": "Track",
        "album": "Album",
        "playlist": "Playlist",
        "artist": "Artist",
    }
    media_type_label = media_type_map.get(media_type.lower(), media_type.capitalize())
    dur_str = f" • {duration // 60}:{duration % 60:02d}" if duration else ""
    dur_formatted = f"{duration // 60}:{duration % 60:02d}" if duration else "0:00"

    context = {
        "title": title or "",
        "artist": artist_name or site_name or "",
        "album": album_name or "",
        "site_name": site_name or "Music Assistant",
        "provider": provider_name or "",
        "media_type": media_type or "track",
        "media_type_label": media_type_label,
        "duration": dur_formatted,
        "duration_str": dur_str,
        "year": str(year) if year else "",
    }

    rendered_author = format_embed_line(author_template, context, site_name or "Music Assistant")
    rendered_title = format_embed_line(title_template, context, title or f"{media_type_label} on {site_name}")
    rendered_desc = format_embed_line(desc_template, context, f"🎵 {media_type_label} by {artist_name or site_name}{dur_str}")
    rendered_footer = format_embed_line(footer_template, context, "").strip()
    if rendered_footer:
        rendered_desc = f"{rendered_desc}\n{rendered_footer}"

    escaped_title = html.escape(rendered_title)
    escaped_desc = html.escape(rendered_desc)
    escaped_site_name = html.escape(rendered_author)
    full_img_url = image_url if image_url.startswith("http") else f"{page_url.split('/s/')[0]}{image_url}"
    escaped_img = html.escape(full_img_url)
    escaped_artist = html.escape(artist_name or site_name)
    base_css = get_base_css(theme_color)

    player_css = (
        f"{base_css}"
        "html,body{width:100%;height:100%;background-color:var(--bg-color);color:var(--text-main);overflow:hidden;display:flex;flex-direction:column;}"
        f".backdrop{{position:fixed;inset:-20%;background-image:url('{escaped_img}');background-size:cover;background-position:center;filter:blur(70px) brightness(0.2) saturate(1.6);z-index:0;transition:background-image 0.5s ease-in-out;pointer-events:none;}}"
        ".top-bar{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;padding:16px 32px;border-bottom:1px solid var(--border);}"
        ".brand{display:flex;align-items:center;gap:12px;font-size:1.1rem;font-weight:700;letter-spacing:0.5px;}"
        ".brand i{color:var(--accent);}"
        ".media-badge{font-size:0.75rem;background:rgba(255,255,255,0.1);padding:4px 10px;border-radius:12px;text-transform:uppercase;letter-spacing:1px;color:var(--accent);border:1px solid rgba(255,255,255,0.1);}"
        ".main-content{position:relative;z-index:1;flex:1;display:flex;padding:32px 48px 16px;gap:48px;overflow:hidden;}"
        ".now-playing-panel{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;max-width:50%;}"
        ".cover-container{width:min(380px,60vh);aspect-ratio:1/1;border-radius:16px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,0.7);background:#111;margin-bottom:24px;border:1px solid var(--border);}"
        ".cover-img{width:100%;height:100%;object-fit:cover;transition:transform 0.3s ease;}"
        ".now-playing-meta{display:flex;flex-direction:column;gap:6px;max-width:80%;}"
        ".now-title{font-size:1.6rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".now-artist{font-size:1.1rem;color:var(--text-muted);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".tracklist-panel{flex:1;display:flex;flex-direction:column;background:var(--panel-bg);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-radius:16px;border:1px solid var(--border);padding:20px;overflow:hidden;}"
        ".tracklist-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--border);font-size:0.95rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;}"
        ".tracklist-scroll{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:4px;padding-right:4px;}"
        ".track-row{display:flex;align-items:center;gap:14px;padding:10px 14px;border-radius:10px;cursor:pointer;transition:background 0.15s ease;}"
        ".track-row:hover{background:rgba(255,255,255,0.06);}"
        ".track-row.active{background:color-mix(in srgb,var(--accent) 15%,transparent);border:1px solid color-mix(in srgb,var(--accent) 35%,transparent);}"
        ".track-row-art{width:44px;height:44px;border-radius:6px;object-fit:cover;background:#222;flex-shrink:0;}"
        ".track-row-info{flex:1;overflow:hidden;display:flex;flex-direction:column;gap:2px;}"
        ".track-row-title{font-size:0.95rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".track-row.active .track-row-title{color:var(--accent);}"
        ".track-row-artist{font-size:0.8rem;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".track-row-dur{font-size:0.85rem;color:var(--text-muted);font-variant-numeric:tabular-nums;}"
        ".player-bar{position:relative;z-index:2;background:rgba(18,16,14,0.9);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);border-top:1px solid var(--border);padding:14px 32px;display:flex;flex-direction:column;gap:8px;}"
        ".scrubber-row{display:flex;align-items:center;gap:12px;width:100%;}"
        ".time-txt{font-size:0.8rem;color:var(--text-muted);font-variant-numeric:tabular-nums;min-width:38px;}"
        ".progress-bar-wrap{flex:1;height:6px;background:rgba(255,255,255,0.15);border-radius:8px;cursor:pointer;position:relative;}"
        ".progress-bar-fill{height:100%;width:0%;background:var(--accent);border-radius:8px;position:relative;}"
        ".controls-row{display:flex;align-items:center;justify-content:space-between;}"
        ".player-side{display:flex;align-items:center;gap:12px;width:25%;}"
        ".center-controls{display:flex;align-items:center;justify-content:center;gap:16px;flex:1;}"
        ".btn-ctrl{background:none;border:none;color:var(--text-muted);font-size:1.1rem;cursor:pointer;padding:8px 12px;border-radius:50%;transition:all 0.2s ease;display:flex;align-items:center;justify-content:center;}"
        ".btn-ctrl:hover{color:#fff;transform:scale(1.1);}"
        ".btn-main-play{background:#fff;color:#000;font-size:1.3rem;width:48px;height:48px;border-radius:50%;box-shadow:0 4px 16px rgba(255,255,255,0.2);}"
        ".btn-main-play:hover{background:var(--accent);color:#fff;transform:scale(1.08);box-shadow:0 6px 24px color-mix(in srgb,var(--accent) 45%,transparent);}"
        ".volume-ctrl{display:flex;align-items:center;gap:10px;width:25%;justify-content:flex-end;}"
        ".vol-slider{accent-color:var(--accent);cursor:pointer;width:90px;}"
        ".tracklist-scroll::-webkit-scrollbar{width:5px;}"
        ".tracklist-scroll::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.2);border-radius:5px;}"
        "@media(max-width:900px){.main-content{flex-direction:column;padding:16px;gap:16px;overflow-y:auto;}.now-playing-panel{max-width:100%;}.cover-container{width:min(240px,40vh);margin-bottom:12px;}.player-side,.volume-ctrl{display:none;}}"
    )

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>{escaped_title} - {escaped_site_name}</title><meta name="description" content="{escaped_desc}"><meta property="og:type" content="music.song"><meta property="og:site_name" content="{escaped_site_name}"><meta property="og:title" content="{escaped_title}"><meta property="og:description" content="{escaped_desc}"><meta property="og:image" content="{escaped_img}"><meta property="og:image:secure_url" content="{escaped_img}"><meta property="og:url" content="{page_url}"><meta property="music:musician" content="{escaped_artist}"><meta name="theme-color" content="{theme_color}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escaped_title}"><meta name="twitter:description" content="{escaped_desc}"><meta name="twitter:image" content="{escaped_img}">{COMMON_FONTS_ICONS}<style>{player_css}</style></head><body><div class="backdrop" id="backdrop"></div><div class="top-bar"><div class="brand"><i class="fa-solid fa-compact-disc fa-spin" style="--fa-animation-duration: 6s;"></i><span>{escaped_site_name}</span></div><span class="media-badge">{media_type.upper()}</span></div><div class="main-content"><div class="now-playing-panel"><div class="cover-container"><img src="{escaped_img}" alt="" class="cover-img" id="artImg"></div><div class="now-playing-meta"><div class="now-title" id="trackTitle">{escaped_title}</div><div class="now-artist" id="trackArtist">{escaped_artist}</div></div></div><div class="tracklist-panel" id="tracklistPanel"><div class="tracklist-header"><span>Tracks</span><span id="trackCount">0</span></div><div class="tracklist-scroll" id="trackList"></div></div></div><div class="player-bar"><div class="scrubber-row"><span class="time-txt" id="currentTime">0:00</span><div class="progress-bar-wrap" id="progressBarWrap"><div class="progress-bar-fill" id="progressBar"></div></div><span class="time-txt" id="duration">0:00</span></div><div class="controls-row"><div class="player-side"><div style="color:var(--text-muted);font-size:0.75rem;display:flex;align-items:center;gap:5px;"><i class="fa-solid fa-bolt" style="color:var(--accent);font-size:0.7rem;"></i><span>Powered by <a href="https://music-assistant.io" target="_blank" rel="noopener noreferrer" style="color:var(--text-muted);text-decoration:underline;transition:color 0.2s ease;" onmouseover="this.style.color='var(--text-main)'" onmouseout="this.style.color='var(--text-muted)'"><strong>Music Assistant</strong></a> and <a href="https://github.com/Bluscream/music-assistant-guest-player" target="_blank" rel="noopener noreferrer" style="color:var(--text-muted);text-decoration:underline;transition:color 0.2s ease;" onmouseover="this.style.color='var(--text-main)'" onmouseout="this.style.color='var(--text-muted)'"><strong>Guest Player</strong></a></span></div></div><div class="center-controls"><button class="btn-ctrl" id="shareBtn" title="Copy Track Link"><i class="fa-solid fa-share-nodes" id="shareIcon"></i></button><button class="btn-ctrl" id="prevBtn" title="Previous"><i class="fa-solid fa-backward-step"></i></button><button class="btn-ctrl btn-main-play" id="playBtn" title="Play/Pause"><i class="fa-solid fa-play" id="playIcon"></i></button><button class="btn-ctrl" id="nextBtn" title="Next"><i class="fa-solid fa-forward-step"></i></button><button class="btn-ctrl" id="loopBtn" title="Loop"><i class="fa-solid fa-repeat"></i></button></div><div class="volume-ctrl"><i class="fa-solid fa-volume-high" style="color:var(--text-muted);font-size:0.9rem;"></i><input type="range" class="vol-slider" id="volSlider" min="0" max="1" step="0.01" value="1"></div></div></div><audio id="audioElement" preload="auto"></audio><script>
const audio=document.getElementById('audioElement'),playBtn=document.getElementById('playBtn'),playIcon=document.getElementById('playIcon'),prevBtn=document.getElementById('prevBtn'),nextBtn=document.getElementById('nextBtn'),loopBtn=document.getElementById('loopBtn'),volSlider=document.getElementById('volSlider'),progressBar=document.getElementById('progressBar'),progressContainer=document.getElementById('progressBarWrap'),currentTimeEl=document.getElementById('currentTime'),durationEl=document.getElementById('duration'),trackTitleEl=document.getElementById('trackTitle'),trackArtistEl=document.getElementById('trackArtist'),artImg=document.getElementById('artImg'),backdrop=document.getElementById('backdrop'),trackListEl=document.getElementById('trackList'),trackCountEl=document.getElementById('trackCount');
let playlist=[],currentIndex=0,isLooping=false,seekOffset=0;
const initialItem={{name:{json.dumps(title)},artist:{json.dumps(artist_name)},image:{json.dumps(image_url)},media_type:{json.dumps(media_type)},stream_url:{json.dumps(stream_url)}}};
function formatTime(s){{if(!isFinite(s)||isNaN(s)||s<0)return'0:00';const m=Math.floor(s/60),sec=Math.floor(s%60);return`${{m}}:${{sec<10?'0':''}}${{sec}}`;}}
const AUTO_PLAY={json.dumps(autoplay)};
function isLiveStream(){{const t=playlist[currentIndex];return !t||!t.duration||t.duration<=0||t.media_type==='radio';}}
function getTrackDuration(){{const t=playlist[currentIndex];if(t&&t.duration&&isFinite(t.duration))return t.duration;if(audio.duration&&isFinite(audio.duration))return audio.duration;return 0;}}
function getInitialTrackIndex(){{const h=window.location.hash.replace(/^#/,'').trim();if(!h)return 0;const n=parseInt(h,10);if(!isNaN(n)){{if(n>=1&&n<=playlist.length)return n-1;if(n>=0&&n<playlist.length)return n;}}const l=decodeURIComponent(h).toLowerCase(),idx=playlist.findIndex(t=>(t.id&&String(t.id).toLowerCase()===l)||(t.name&&t.name.toLowerCase()===l));return idx!==-1?idx:0;}}
async function loadData(){{try{{const res=await fetch('{api_url}'),data=await res.json();if(data.tracks&&data.tracks.length>0){{playlist=data.tracks;trackCountEl.textContent=`${{playlist.length}}`;renderTracklist();setTrack(getInitialTrackIndex(),AUTO_PLAY);}}else{{playlist=[initialItem];trackCountEl.textContent='1';renderTracklist();setTrack(0,AUTO_PLAY);}}}}catch(e){{playlist=[initialItem];trackCountEl.textContent='1';renderTracklist();setTrack(0,AUTO_PLAY);}}}}
window.addEventListener('hashchange',()=>{{const idx=getInitialTrackIndex();if(idx!==currentIndex)setTrack(idx,!audio.paused);}});
function renderTracklist(){{trackListEl.innerHTML='';playlist.forEach((t,idx)=>{{const row=document.createElement('div');row.className=`track-row ${{idx===currentIndex?'active':''}}`;const img=t.image||'{escaped_img}';const durLabel=(t.duration&&t.duration>0)?formatTime(t.duration):'LIVE';row.innerHTML=`<img src="${{img}}" class="track-row-art" alt=""><div class="track-row-info"><span class="track-row-title">${{t.name}}</span><span class="track-row-artist">${{t.artist||'{escaped_site_name}'}}</span></div><span class="track-row-dur">${{durLabel}}</span>`;row.onclick=()=>setTrack(idx,true);trackListEl.appendChild(row);}});}}
function setTrack(idx,play=true,offset=0){{if(idx<0||idx>=playlist.length)return;currentIndex=idx;seekOffset=offset;const t=playlist[idx];trackTitleEl.textContent=t.name;trackArtistEl.textContent=t.artist||'{escaped_site_name}';const img=t.image||'{escaped_img}';artImg.src=img;backdrop.style.backgroundImage=`url('${{img}}')`;let base=t.stream_url.startsWith('http')?t.stream_url:window.location.origin+t.stream_url;const join=base.includes('?')?'&':'?';audio.src=`${{base}}${{join}}offset=${{Math.floor(offset)}}&_t=${{Date.now()}}`;audio.load();if(playlist.length>1)history.replaceState(null,'',`#${{t.id||(idx+1)}}`);const isLive=isLiveStream(),dur=getTrackDuration();durationEl.textContent=isLive?'LIVE':formatTime(dur);durationEl.style.color=isLive?'var(--accent)':'var(--text-muted)';durationEl.style.fontWeight=isLive?'700':'400';progressBar.style.width=isLive?'100%':((dur>0?Math.min(100,Math.max(0,(offset/dur)*100)):0)+'%');progressContainer.style.cursor=isLive?'default':'pointer';currentTimeEl.textContent=formatTime(offset);renderTracklist();if('mediaSession'in navigator)navigator.mediaSession.metadata=new MediaMetadata({{title:t.name,artist:t.artist,artwork:[{{src:img}}]}});if(play){{audio.play().catch(e=>{{console.log('Autoplay prevented:',e);const unlock=()=>{{audio.play().catch(()=>{{}});window.removeEventListener('click',unlock);window.removeEventListener('keydown',unlock);window.removeEventListener('touchstart',unlock);}};window.addEventListener('click',unlock,{{once:true}});window.addEventListener('keydown',unlock,{{once:true}});window.addEventListener('touchstart',unlock,{{once:true}});}});}}}}
playBtn.onclick=()=>{{if(!audio.src||audio.src===''||audio.src===window.location.href){{setTrack(currentIndex,true,seekOffset);return;}}if(audio.paused)audio.play().catch(e=>console.log('Playback error:',e));else audio.pause();}};
audio.onplay=()=>{{playIcon.className='fa-solid fa-pause';}};
audio.onpause=()=>{{playIcon.className='fa-solid fa-play';}};
audio.ontimeupdate=()=>{{const isLive=isLiveStream(),dur=getTrackDuration(),cur=seekOffset+(isFinite(audio.currentTime)?audio.currentTime:0);if(isLive){{progressBar.style.width='100%';durationEl.textContent='LIVE';}}else if(dur>0){{progressBar.style.width=Math.min(100,Math.max(0,(cur/dur)*100))+'%';durationEl.textContent=formatTime(dur);}}currentTimeEl.textContent=formatTime(cur);}};
audio.onloadedmetadata=()=>{{const isLive=isLiveStream();durationEl.textContent=isLive?'LIVE':formatTime(getTrackDuration());}};
audio.onended=()=>{{if(isLooping)setTrack(currentIndex,true,0);else if(currentIndex+1<playlist.length)setTrack(currentIndex+1,true,0);else playIcon.className='fa-solid fa-play';}};
const shareBtn=document.getElementById('shareBtn'),shareIcon=document.getElementById('shareIcon');
shareBtn.onclick=async()=>{{const t=playlist[currentIndex]||initialItem;let url=(t&&t.provider&&t.id)?`${{window.location.origin}}/s/track/${{t.provider}}/${{encodeURIComponent(t.id)}}`:window.location.href.split('#')[0];try{{if(navigator.clipboard&&navigator.clipboard.writeText)await navigator.clipboard.writeText(url);else{{const tmp=document.createElement('input');tmp.value=url;document.body.appendChild(tmp);tmp.select();document.execCommand('copy');document.body.removeChild(tmp);}}shareIcon.className='fa-solid fa-check';shareBtn.style.color='var(--accent)';setTimeout(()=>{{shareIcon.className='fa-solid fa-share-nodes';shareBtn.style.color='';}},2000);}}catch(e){{console.error('Failed to copy:',e);}}}};
prevBtn.onclick=()=>{{if(isLiveStream())return;const cur=seekOffset+(isFinite(audio.currentTime)?audio.currentTime:0);if(cur>3)setTrack(currentIndex,!audio.paused,0);else if(currentIndex>0)setTrack(currentIndex-1,true,0);}};
nextBtn.onclick=()=>{{if(currentIndex+1<playlist.length)setTrack(currentIndex+1,true,0);}};
loopBtn.onclick=()=>{{isLooping=!isLooping;loopBtn.style.color=isLooping?'var(--accent)':'var(--text-muted)';}};
const savedVol=localStorage.getItem('guest_player_vol');
if(savedVol!==null){{const v=parseFloat(savedVol);if(!isNaN(v)&&v>=0&&v<=1){{volSlider.value=v;audio.volume=v;}}}}else{{audio.volume=parseFloat(volSlider.value)||1;}}
volSlider.oninput=e=>{{const v=parseFloat(e.target.value);audio.volume=v;localStorage.setItem('guest_player_vol',v);}};
progressContainer.onclick=e=>{{if(isLiveStream())return;const dur=getTrackDuration();if(!dur||dur<=0)return;const rect=progressContainer.getBoundingClientRect(),pos=Math.min(1,Math.max(0,(e.clientX-rect.left)/rect.width));setTrack(currentIndex,!audio.paused,pos*dur);}};
loadData();
</script></body></html>"""


def render_link_generator_page(
    site_name: str,
    theme_color: str,
    base_url: str,
) -> str:
    """Generate minimal link generator UI with only the input box."""
    escaped_site_name = html.escape(site_name)
    base_css = get_base_css(theme_color, panel_bg="rgba(28, 25, 23, 0.85)", border="rgba(255, 255, 255, 0.1)")
    gen_css = (
        f"{base_css}"
        "html,body{width:100%;height:100%;background-color:var(--bg-color);color:var(--text-main);display:flex;align-items:center;justify-content:center;padding:24px;overflow:hidden;}"
        f".backdrop{{position:fixed;inset:-20%;background:radial-gradient(circle at center,color-mix(in srgb,var(--accent) 25%,transparent) 0%,rgba(20,18,16,0.98) 70%);z-index:0;pointer-events:none;}}"
        ".url-input{position:relative;z-index:1;width:100%;max-width:640px;background:rgba(28,25,23,0.85);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border:1px solid var(--border);border-radius:16px;padding:18px 24px;font-size:1.05rem;color:var(--text-main);box-shadow:0 20px 40px rgba(0,0,0,0.5);outline:none;transition:all 0.25s ease;}"
        ".url-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent),0 20px 40px rgba(0,0,0,0.6);}"
    )

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>Link Generator - {escaped_site_name}</title>{COMMON_FONTS}<style>{gen_css}</style></head><body><div class="backdrop"></div><input type="text" class="url-input" id="urlInput" placeholder="Paste Music Assistant URL to convert..." autocomplete="off" spellcheck="false" autofocus><script>
const input=document.getElementById('urlInput'),BASE_URL='{base_url}'||window.location.origin;
function convertUrl(v){{v=v.trim();if(!v)return'';const h=v.match(/#\\/?(tracks|albums|playlists|artists|radios|track|album|playlist|artist|radio)\\/(.+)$/i);if(h){{let p=h[2].split('/'),t=h[1].toLowerCase().replace(/s$/,'');return`${{BASE_URL}}/s/${{t}}/${{p[0]}}/${{p.slice(1).join('/')}}`;}}const m=v.match(/\\b(tracks|albums|playlists|artists|radios|track|album|playlist|artist|radio)\\/(.+)$/i);if(m&&!v.includes('/s/')){{let p=m[2].split('/'),t=m[1].toLowerCase().replace(/s$/,'');return`${{BASE_URL}}/s/${{t}}/${{p[0]}}/${{p.slice(1).join('/')}}`;}}return v;}}
function handleConvert(){{const orig=input.value,conv=convertUrl(orig);if(conv&&conv!==orig){{input.value=conv;input.select();}}}}
input.addEventListener('input',handleConvert);
input.addEventListener('paste',()=>setTimeout(handleConvert,20));
</script></body></html>"""
