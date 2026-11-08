"""HyperFrames-based 2D Character Animation Engine for 1080x1920 Vertical Shorts.
Renders 100% code-driven animated videos with GSAP squash & stretch, eye blinks,
kinetic captions, interactive counting badges, confetti celebrations, and beat-synced audio.
Watermark-free, professional broadcast quality.
"""
import asyncio
import json
import math
import os
import shutil
import subprocess
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def generate_hf_html(script, audio_rel_path, duration_sec=30.0):
    """Generates the master index.html for HyperFrames with SVG character rigs & GSAP timeline."""
    title_en = script.get("title_en", "The Magic Bus Ride")
    scenes = script.get("scenes", [])
    n_scenes = max(1, len(scenes))
    scene_dur = duration_sec / n_scenes
    
    # Kinetic caption items
    caption_elements = []
    caption_tweens = []
    
    for i, s in enumerate(scenes):
        t_start = i * scene_dur
        t_end = (i + 1) * scene_dur
        cid = f"cap_{i}"
        txt = s.get("text", "").replace("\\n", "<br/>").replace("\n", "<br/>")
        caption_elements.append(f"""
          <div id="{cid}" class="caption-card" style="opacity: 0; transform: translateY(30px) scale(0.85);">
            <div class="cap-bubble">
              <span class="cap-text">{txt}</span>
            </div>
          </div>
        """)
        # GSAP tween: Pop in with elastic bounce, hold, then exit with quick blur-fade
        caption_tweens.append(f"""
          // Caption {i}
          tl.to("#{cid}", {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(1.8)" }}, {t_start:.2f});
          tl.to("#{cid}", {{ opacity: 0, y: -20, scale: 0.9, duration: 0.25, ease: "power2.in" }}, {t_end - 0.25:.2f});
        """)

    captions_html = "\n".join(caption_elements)
    captions_js = "\n".join(caption_tweens)

    # Confetti DOM elements
    confetti_elements = []
    colors = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#facc15"]
    for c_idx in range(35):
        color = colors[c_idx % len(colors)]
        left_pos = (c_idx * 29) % 1020 + 30
        confetti_elements.append(f'<div id="confetti-{c_idx}" class="confetti-piece" style="left: {left_pos}px; background: {color};"></div>')
    confetti_html = "\n".join(confetti_elements)

    html = f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>{title_en}</title>
    <script src="assets/gsap.min.js"></script>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@600;700;800&family=Noto+Sans+Devanagari:wght@700;800&display=swap');

      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        width: 1080px; height: 1920px; overflow: hidden;
        background: #0f172a;
        font-family: 'Fredoka', 'Noto Sans Devanagari', sans-serif;
      }}
      #root {{
        position: relative; width: 1080px; height: 1920px;
        overflow: hidden;
      }}

      /* Sky and Environment */
      .sky-bg {{
        position: absolute; inset: 0;
        background: linear-gradient(180deg, #38bdf8 0%, #7dd3fc 45%, #bae6fd 75%, #fef08a 100%);
      }}
      .sun {{
        position: absolute; top: 90px; right: 90px;
        width: 170px; height: 170px;
      }}
      .cloud {{
        position: absolute; fill: #ffffff; opacity: 0.92;
        filter: drop-shadow(0 8px 16px rgba(0,0,0,0.06));
      }}
      .hills-back {{
        position: absolute; bottom: 420px; left: -100px; width: 1280px; height: 480px;
        fill: #86efac;
      }}
      .hills-front {{
        position: absolute; bottom: 320px; left: -80px; width: 1240px; height: 420px;
        fill: #4ade80;
      }}

      /* Curving Cartoon Road */
      .road-container {{
        position: absolute; bottom: 0; left: 0; width: 1080px; height: 380px;
        background: #334155;
        border-top: 18px solid #22c55e;
        overflow: hidden;
      }}
      .road-dashes {{
        position: absolute; top: 160px; left: -400px; width: 2200px; height: 28px;
        display: flex; gap: 80px;
      }}
      .dash {{
        width: 110px; height: 24px; background: #facc15; border-radius: 12px;
      }}

      /* Magic Bus */
      #magic-bus {{
        position: absolute; bottom: 220px; left: 100px;
        width: 880px; height: 560px;
        filter: drop-shadow(0 25px 30px rgba(15, 23, 42, 0.40));
        transform-origin: center bottom;
        z-index: 15;
      }}
      .wheel {{
        transform-origin: center center;
      }}

      /* Character: Chintu the Baby Elephant */
      #chintu-char {{
        position: absolute; bottom: 420px; left: 340px;
        width: 380px; height: 420px;
        filter: drop-shadow(0 14px 18px rgba(0,0,0,0.22));
        transform-origin: bottom center;
        z-index: 25;
      }}
      .chintu-ear {{
        transform-origin: 30% 20%;
      }}
      .chintu-trunk {{
        transform-origin: 50% 15%;
      }}
      .chintu-eye {{
        transform-origin: center center;
      }}

      /* Character: Mithu the Parrot */
      #mithu-char {{
        position: absolute; top: 460px; right: 100px;
        width: 280px; height: 300px;
        filter: drop-shadow(0 12px 16px rgba(0,0,0,0.20));
        transform-origin: center center;
        z-index: 30;
      }}
      .mithu-wing {{
        transform-origin: top right;
      }}

      /* Counting Numbers Badges (Scene 4) */
      .count-badge-wrap {{
        position: absolute; top: 640px; left: 0; width: 1080px;
        display: flex; justify-content: center; gap: 40px;
        z-index: 50; pointer-events: none;
      }}
      .count-badge {{
        width: 140px; height: 140px; border-radius: 70px;
        display: flex; align-items: center; justify-content: center;
        font-size: 72px; font-weight: 800; color: #ffffff;
        box-shadow: 0 16px 32px rgba(0,0,0,0.35);
        border: 6px solid #ffffff;
        opacity: 0; transform: scale(0.2);
      }}
      #num-1 {{ background: #ef4444; }}
      #num-2 {{ background: #3b82f6; }}
      #num-3 {{ background: #10b981; }}

      /* Confetti Particles (Scene 5) */
      .confetti-piece {{
        position: absolute; top: -60px;
        width: 22px; height: 28px; border-radius: 6px;
        opacity: 0; z-index: 60; pointer-events: none;
      }}

      /* Floating Sparkles & Musical Notes */
      .music-note {{
        position: absolute; font-size: 64px;
        opacity: 0; pointer-events: none; z-index: 25;
      }}

      /* Kinetic Candy Captions (Safe Golden Zone: top 230px) */
      #captions-box {{
        position: absolute; top: 230px; left: 0; width: 1080px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        z-index: 100; pointer-events: none;
      }}
      .caption-card {{
        position: absolute;
        display: flex; align-items: center; justify-content: center;
        width: 920px;
      }}
      .cap-bubble {{
        background: rgba(15, 23, 42, 0.94);
        border: 7px solid #facc15;
        border-radius: 36px;
        padding: 20px 42px;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45), 0 0 30px rgba(250, 204, 21, 0.50);
        text-align: center;
      }}
      .cap-text {{
        font-size: 46px; font-weight: 800; line-height: 1.30;
        color: #ffffff;
        text-shadow: 0 4px 12px rgba(0,0,0,0.7);
        -webkit-text-stroke: 1.5px #1e1b4b;
      }}

      /* Top Hook Badge */
      .top-badge {{
        position: absolute; top: 80px; left: 60px;
        background: #ef4444; color: #ffffff;
        font-size: 32px; font-weight: 800;
        padding: 12px 28px; border-radius: 24px;
        border: 4px solid #fde047;
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        letter-spacing: 0.05em;
        z-index: 120;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration_sec:.1f}" data-width="1080" data-height="1920">
      
      <!-- Sky Background -->
      <div class="sky-bg"></div>

      <!-- Smiling Animated Sun -->
      <svg class="sun" id="sun-svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="32" fill="#FBBF24" />
        <circle cx="50" cy="50" r="28" fill="#FDE047" />
        <!-- Sun Face -->
        <circle cx="41" cy="46" r="3" fill="#78350F" />
        <circle cx="59" cy="46" r="3" fill="#78350F" />
        <path d="M 42 54 Q 50 62 58 54" stroke="#78350F" stroke-width="3" stroke-linecap="round" fill="none" />
        <circle cx="36" cy="51" r="3.5" fill="#F87171" opacity="0.6" />
        <circle cx="64" cy="51" r="3.5" fill="#F87171" opacity="0.6" />
      </svg>

      <!-- Drifting Clouds -->
      <svg class="cloud" id="cloud-1" style="top: 140px; left: -100px; width: 340px; height: 160px;" viewBox="0 0 100 50">
        <path d="M 10 38 Q 12 18 32 18 Q 42 6 62 14 Q 82 10 88 28 Q 98 34 88 44 Q 50 48 10 38 Z" />
      </svg>
      <svg class="cloud" id="cloud-2" style="top: 280px; left: 700px; width: 280px; height: 130px;" viewBox="0 0 100 50">
        <path d="M 10 38 Q 12 18 32 18 Q 42 6 62 14 Q 82 10 88 28 Q 98 34 88 44 Q 50 48 10 38 Z" />
      </svg>

      <!-- Rolling Green Hills -->
      <svg class="hills-back" viewBox="0 0 1200 400" preserveAspectRatio="none">
        <path d="M 0 200 Q 350 40 700 180 T 1200 120 L 1200 400 L 0 400 Z" />
      </svg>
      <svg class="hills-front" viewBox="0 0 1200 400" preserveAspectRatio="none">
        <path d="M 0 160 Q 400 300 800 120 T 1200 220 L 1200 400 L 0 400 Z" />
      </svg>

      <!-- Moving Road -->
      <div class="road-container">
        <div class="road-dashes" id="road-dashes">
          <div class="dash"></div><div class="dash"></div><div class="dash"></div>
          <div class="dash"></div><div class="dash"></div><div class="dash"></div>
          <div class="dash"></div><div class="dash"></div><div class="dash"></div>
        </div>
      </div>

      <!-- Magic Yellow Bus (SVG Rig) -->
      <div id="magic-bus">
        <svg viewBox="0 0 500 300" width="100%" height="100%">
          <!-- Bus Main Body -->
          <rect x="50" y="50" width="400" height="180" rx="36" fill="#FACC15" stroke="#CA8A04" stroke-width="8" />
          <!-- Bus Roof Dome -->
          <path d="M 80 50 Q 250 20 420 50 Z" fill="#FDE047" />
          <!-- Shiny Windows -->
          <rect x="80" y="80" width="90" height="75" rx="14" fill="#38BDF8" stroke="#0284C7" stroke-width="5" />
          <rect x="190" y="80" width="90" height="75" rx="14" fill="#38BDF8" stroke="#0284C7" stroke-width="5" />
          <rect x="300" y="80" width="120" height="75" rx="14" fill="#38BDF8" stroke="#0284C7" stroke-width="5" />
          <!-- Windshield Highlight Reflection -->
          <line x1="90" y1="90" x2="150" y2="145" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" opacity="0.7" />
          <line x1="310" y1="90" x2="390" y2="145" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" opacity="0.7" />
          <!-- Headlights -->
          <circle cx="435" cy="175" r="18" fill="#FEF08A" stroke="#EAB308" stroke-width="4" />
          <circle cx="435" cy="175" r="8" fill="#FFFFFF" />
          <!-- Front Grille Smile -->
          <path d="M 400 200 Q 425 215 445 200" stroke="#713F12" stroke-width="6" stroke-linecap="round" fill="none" />
          <!-- Wheels -->
          <g id="wheel-front" class="wheel">
            <circle cx="370" cy="235" r="42" fill="#1E293B" stroke="#475569" stroke-width="8" />
            <circle cx="370" cy="235" r="18" fill="#E2E8F0" />
            <circle cx="370" cy="235" r="6" fill="#0F172A" />
          </g>
          <g id="wheel-back" class="wheel">
            <circle cx="130" cy="235" r="42" fill="#1E293B" stroke="#475569" stroke-width="8" />
            <circle cx="130" cy="235" r="18" fill="#E2E8F0" />
            <circle cx="130" cy="235" r="6" fill="#0F172A" />
          </g>
        </svg>
      </div>

      <!-- Chintu the Baby Elephant (SVG Character Rig) -->
      <div id="chintu-char">
        <svg viewBox="0 0 300 320" width="100%" height="100%">
          <!-- Left Ear -->
          <g id="chintu-left-ear" class="chintu-ear">
            <ellipse cx="65" cy="130" rx="55" ry="70" fill="#FB923C" stroke="#EA580C" stroke-width="6" />
            <ellipse cx="65" cy="130" rx="35" ry="45" fill="#FDBA74" />
          </g>
          <!-- Body -->
          <ellipse cx="150" cy="220" rx="80" ry="75" fill="#FB923C" stroke="#EA580C" stroke-width="6" />
          <!-- Scarf -->
          <path d="M 95 185 Q 150 215 205 185 Q 215 205 195 220 Q 150 235 105 220 Z" fill="#0284C7" stroke="#0369A1" stroke-width="4" />
          <path d="M 160 215 L 180 270 L 155 265 Z" fill="#38BDF8" stroke="#0369A1" stroke-width="3" />
          <!-- Head -->
          <ellipse cx="150" cy="125" rx="75" ry="70" fill="#FB923C" stroke="#EA580C" stroke-width="6" />
          <!-- Right Ear -->
          <g id="chintu-right-ear" class="chintu-ear">
            <ellipse cx="235" cy="130" rx="55" ry="70" fill="#FB923C" stroke="#EA580C" stroke-width="6" />
            <ellipse cx="235" cy="130" rx="35" ry="45" fill="#FDBA74" />
          </g>
          <!-- Eyes with Double Catchlights -->
          <g id="chintu-eyes" class="chintu-eye">
            <!-- Left Eye -->
            <ellipse cx="120" cy="115" rx="14" ry="18" fill="#1E293B" />
            <circle cx="116" cy="109" r="6" fill="#FFFFFF" />
            <circle cx="123" cy="122" r="2.5" fill="#FFFFFF" />
            <!-- Right Eye -->
            <ellipse cx="180" cy="115" rx="14" ry="18" fill="#1E293B" />
            <circle cx="176" cy="109" r="6" fill="#FFFFFF" />
            <circle cx="183" cy="122" r="2.5" fill="#FFFFFF" />
          </g>
          <!-- Rosy Cheeks -->
          <ellipse cx="100" cy="135" rx="12" ry="8" fill="#F43F5E" opacity="0.45" />
          <ellipse cx="200" cy="135" rx="12" ry="8" fill="#F43F5E" opacity="0.45" />
          <!-- Elephant Trunk -->
          <g id="chintu-trunk" class="chintu-trunk">
            <path d="M 140 135 Q 150 175 140 195 Q 135 210 155 215 Q 170 210 160 190 Q 165 170 160 135 Z" fill="#FB923C" stroke="#EA580C" stroke-width="5" />
          </g>
        </svg>
      </div>

      <!-- Mithu the Parrot (SVG Character Rig) -->
      <div id="mithu-char">
        <svg viewBox="0 0 240 260" width="100%" height="100%">
          <!-- Left Wing -->
          <g id="mithu-wing" class="mithu-wing">
            <path d="M 60 110 Q 15 140 45 180 Q 75 170 80 140 Z" fill="#16A34A" stroke="#15803D" stroke-width="5" />
          </g>
          <!-- Body -->
          <ellipse cx="120" cy="140" rx="55" ry="65" fill="#22C55E" stroke="#15803D" stroke-width="6" />
          <!-- Yellow Chest -->
          <ellipse cx="120" cy="155" rx="35" ry="42" fill="#FACC15" />
          <!-- Head -->
          <circle cx="120" cy="85" r="45" fill="#22C55E" stroke="#15803D" stroke-width="6" />
          <!-- Red Beanie Cap -->
          <path d="M 85 70 Q 120 40 155 70 Z" fill="#EF4444" stroke="#B91C1C" stroke-width="4" />
          <circle cx="120" cy="42" r="10" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="3" />
          <!-- Eye -->
          <circle cx="138" cy="82" r="12" fill="#FFFFFF" stroke="#0F172A" stroke-width="3" />
          <circle cx="140" cy="82" r="7" fill="#0F172A" />
          <circle cx="138" cy="79" r="3" fill="#FFFFFF" />
          <!-- Orange Beak -->
          <path d="M 155 85 Q 190 92 170 115 Q 148 102 155 85 Z" fill="#F97316" stroke="#C2410C" stroke-width="4" />
        </svg>
      </div>

      <!-- Interactive 1, 2, 3 Counting Badges (Scene 4) -->
      <div class="count-badge-wrap">
        <div id="num-1" class="count-badge">1</div>
        <div id="num-2" class="count-badge">2</div>
        <div id="num-3" class="count-badge">3</div>
      </div>

      <!-- Confetti Particles (Scene 5) -->
      {confetti_html}

      <!-- Musical Notes Particles -->
      <div id="note-1" class="music-note" style="top: 720px; left: 160px; color: #f43f5e;">🎶</div>
      <div id="note-2" class="music-note" style="top: 680px; left: 820px; color: #8b5cf6;">⭐</div>
      <div id="note-3" class="music-note" style="top: 860px; left: 480px; color: #f59e0b;">✨</div>

      <!-- Top Hook Badge -->
      <div class="top-badge">🌟 RANGEELA RHYMES</div>

      <!-- Kinetic Captions Container -->
      <div id="captions-box">
        {captions_html}
      </div>

      <!-- Master Audio Track -->
      <audio id="master-audio" src="{audio_rel_path}" preload="auto"></audio>

    </div>

    <!-- GSAP Master Animation Timeline -->
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;

      // 1. Environment Parallax & Sunlight
      tl.to("#sun-svg", {{ rotation: 360, transformOrigin: "center center", duration: {duration_sec:.1f}, ease: "none" }}, 0);
      tl.to("#cloud-1", {{ x: 1200, duration: {duration_sec:.1f}, ease: "none" }}, 0);
      tl.to("#cloud-2", {{ x: -1100, duration: {duration_sec:.1f}, ease: "none" }}, 0);
      tl.to("#road-dashes", {{ x: -400, repeat: -1, duration: 0.6, ease: "none" }}, 0);

      // 2. Bus Suspension Bounce & Wheel Rotation
      tl.to("#magic-bus", {{ y: -16, duration: 0.28, repeat: -1, yoyo: true, ease: "sine.inOut" }}, 0);
      tl.to("#wheel-front", {{ rotation: 360 * {int(duration_sec * 2)}, transformOrigin: "370px 235px", duration: {duration_sec:.1f}, ease: "none" }}, 0);
      tl.to("#wheel-back", {{ rotation: 360 * {int(duration_sec * 2)}, transformOrigin: "130px 235px", duration: {duration_sec:.1f}, ease: "none" }}, 0);

      // 3. Chintu Elephant Acting (Squash & Stretch Jumping, Ear Wiggling, Trunk Sway, Eye Blinking)
      const hopCount = Math.floor({duration_sec:.1f} / 1.8);
      for (let h = 0; h < hopCount; h++) {{
        const tHop = h * 1.8;
        // Anticipation squash
        tl.to("#chintu-char", {{ scaleX: 1.08, scaleY: 0.92, duration: 0.15, ease: "power2.in" }}, tHop);
        // Upward jump stretch
        tl.to("#chintu-char", {{ y: -140, scaleX: 0.92, scaleY: 1.12, duration: 0.35, ease: "power2.out" }}, tHop + 0.15);
        // Landing bounce
        tl.to("#chintu-char", {{ y: 0, scaleX: 1.07, scaleY: 0.93, duration: 0.25, ease: "bounce.out" }}, tHop + 0.50);
        // Settle
        tl.to("#chintu-char", {{ scaleX: 1.0, scaleY: 1.0, duration: 0.20, ease: "power1.out" }}, tHop + 0.75);

        // Ear wiggles during jump
        tl.to("#chintu-left-ear", {{ rotation: -20, duration: 0.25, yoyo: true, repeat: 1, ease: "sine.inOut" }}, tHop + 0.15);
        tl.to("#chintu-right-ear", {{ rotation: 20, duration: 0.25, yoyo: true, repeat: 1, ease: "sine.inOut" }}, tHop + 0.15);

        // Trunk cheerful curl
        tl.to("#chintu-trunk", {{ rotation: 24, duration: 0.35, yoyo: true, repeat: 1, ease: "back.out(2)" }}, tHop + 0.20);
      }}

      // Natural Eye Blinks every 2.4 seconds
      const blinkCount = Math.floor({duration_sec:.1f} / 2.4);
      for (let b = 0; b < blinkCount; b++) {{
        const tBlink = b * 2.4 + 0.6;
        tl.to("#chintu-eyes", {{ scaleY: 0.08, duration: 0.08, yoyo: true, repeat: 1, ease: "power2.inOut" }}, tBlink);
      }}

      // 4. Mithu Parrot Flying & Fluttering
      tl.to("#mithu-char", {{ y: -45, x: -30, rotation: -6, duration: 0.8, repeat: -1, yoyo: true, ease: "sine.inOut" }}, 0);
      tl.to("#mithu-wing", {{ rotation: -40, duration: 0.12, repeat: -1, yoyo: true, ease: "sine.inOut" }}, 0);

      // 5. Counting Numbers Animation (Scene 4: ~15s to 20s)
      tl.to("#num-1", {{ opacity: 1, scale: 1.15, duration: 0.45, ease: "back.out(2.2)" }}, 15.2);
      tl.to("#num-1", {{ scale: 1.0, duration: 0.2 }}, 15.65);
      tl.to("#num-2", {{ opacity: 1, scale: 1.15, duration: 0.45, ease: "back.out(2.2)" }}, 16.5);
      tl.to("#num-2", {{ scale: 1.0, duration: 0.2 }}, 16.95);
      tl.to("#num-3", {{ opacity: 1, scale: 1.15, duration: 0.45, ease: "back.out(2.2)" }}, 17.8);
      tl.to("#num-3", {{ scale: 1.0, duration: 0.2 }}, 18.25);
      // Hide numbers before scene 5
      tl.to(".count-badge", {{ opacity: 0, scale: 0.5, duration: 0.35, ease: "power2.in" }}, 19.6);

      // 6. Confetti Shower (Scene 5: ~20s to 25s)
      for (let c = 0; c < 35; c++) {{
        const delay = 20.0 + (c % 7) * 0.25;
        const dur = 2.2 + (c % 5) * 0.3;
        const rot = (c % 2 === 0 ? 360 : -360) * 2;
        tl.fromTo("#confetti-" + c, 
          {{ opacity: 1, y: 0, rotation: 0 }},
          {{ y: 1980, rotation: rot, duration: dur, ease: "none" }}, 
          delay
        );
      }}

      // 7. Musical Sparkle Bursts
      tl.to("#note-1", {{ opacity: 1, y: -90, scale: 1.4, duration: 1.2, repeat: -1, repeatDelay: 1.4, ease: "power1.out" }}, 0.3);
      tl.to("#note-2", {{ opacity: 1, y: -120, rotation: 45, duration: 1.4, repeat: -1, repeatDelay: 1.8, ease: "power1.out" }}, 1.0);
      tl.to("#note-3", {{ opacity: 1, y: -80, scale: 1.3, duration: 1.1, repeat: -1, repeatDelay: 1.2, ease: "power1.out" }}, 1.7);

      // 8. Kinetic Caption Sequence
      {captions_js}

      // Seek to start
      tl.seek(0);
    </script>
  </body>
</html>"""
    return html


def build_master_audio(script, out_audio_path, work_dir, duration_sec=30.0):
    """Mixes background music, synthesized dialogue, and synchronized Foley effects into out_audio_path."""
    scenes = script.get("scenes", [])
    n_scenes = max(1, len(scenes))
    scene_dur = duration_sec / n_scenes

    # Ensure sfx catalog
    import sfx
    sfx.ensure_sfx_catalog()

    # Base background music
    bgm_candidates = [os.path.join(ROOT, "music", f) for f in os.listdir(os.path.join(ROOT, "music")) if f.endswith((".mp3", ".wav"))]
    bgm_file = bgm_candidates[0] if bgm_candidates else None
    if not bgm_file or not os.path.exists(bgm_file):
        raise RuntimeError("Nursery BGM file missing in music/ directory")

    # Synthesize vocals for each scene line
    import edge_tts
    dialogue_wavs = []
    
    async def syn_all():
        for i, s in enumerate(scenes):
            txt = s.get("text", "")
            lang = s.get("lang", "hi")
            voice = "hi-IN-SwaraNeural" if lang == "hi" else "en-IN-NeerjaNeural"
            out_v = os.path.join(work_dir, f"voice_{i:02d}.mp3")
            try:
                await edge_tts.Communicate(txt, voice, pitch="+14Hz", rate="+12%").save(out_v)
                dialogue_wavs.append((i, out_v))
            except Exception as e:
                print(f"[hf-audio] edge-tts error for scene {i}: {e}")

    try:
        asyncio.run(asyncio.wait_for(syn_all(), timeout=45))
    except Exception as e:
        print(f"[hf-audio] TTS batch error: {e}")

    # Build complex FFmpeg audio filtergraph
    # Inputs:
    # 0: BGM (looped and cut to duration_sec)
    # 1..N: Voice tracks delayed to scene start
    # Foley sound effects delayed to cue timestamps
    foley_cues = [
        (0.4, os.path.join(ROOT, "sfx", "chime.wav")),
        (5.2, os.path.join(ROOT, "sfx", "boing.wav")),
        (10.2, os.path.join(ROOT, "sfx", "ding.wav")),
        (15.2, os.path.join(ROOT, "sfx", "pop.wav")),
        (20.2, os.path.join(ROOT, "sfx", "cheer.wav")),
        (25.2, os.path.join(ROOT, "sfx", "whoosh.wav")),
    ]
    existing_foleys = [(t, p) for t, p in foley_cues if os.path.exists(p)]

    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", bgm_file]
    input_idx = 1
    v_inputs = []
    for sc_idx, v_path in dialogue_wavs:
        if os.path.exists(v_path):
            cmd.extend(["-i", v_path])
            v_inputs.append((sc_idx, input_idx))
            input_idx += 1

    f_inputs = []
    for t_cue, f_path in existing_foleys:
        cmd.extend(["-i", f_path])
        f_inputs.append((t_cue, input_idx))
        input_idx += 1

    # Filtergraph construction
    filter_chains = []
    # 1. BGM ducking and fade out
    filter_chains.append(f"[0:a]atrim=0:{duration_sec:.2f},volume=0.22,afade=t=in:st=0:d=0.4,afade=t=out:st={duration_sec-0.5:.2f}:d=0.5[a_bgm]")

    # 2. Delayed Vocals
    mix_sources = ["[a_bgm]"]
    for sc_idx, in_id in v_inputs:
        delay_ms = int(sc_idx * scene_dur * 1000)
        filter_chains.append(f"[{in_id}:a]adelay={delay_ms}|{delay_ms},volume=1.0[v_{sc_idx}]")
        mix_sources.append(f"[v_{sc_idx}]")

    # 3. Delayed Foleys
    for f_idx, (t_cue, in_id) in enumerate(f_inputs):
        delay_ms = int(t_cue * 1000)
        filter_chains.append(f"[{in_id}:a]adelay={delay_ms}|{delay_ms},volume=0.50[f_{f_idx}]")
        mix_sources.append(f"[f_{f_idx}]")

    # 4. Amix
    total_mix = len(mix_sources)
    filter_chains.append(f"{''.join(mix_sources)}amix=inputs={total_mix}:duration=first:dropout_transition=2[a_out]")

    full_filter = ";".join(filter_chains)
    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[a_out]",
        "-t", f"{duration_sec:.2f}",
        "-ar", "48000",
        "-ac", "2",
        "-b:a", "192k",
        out_audio_path
    ])

    print(f"[hf-audio] Mixing master audio track -> {out_audio_path}...")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"[hf-audio] Complex mix warning: {p.stderr[:300]}, falling back to direct BGM")
        # Direct fallback: BGM trimmed with fade
        fallback_cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", bgm_file,
            "-t", f"{duration_sec:.2f}",
            "-af", f"volume=0.45,afade=t=in:st=0:d=0.3,afade=t=out:st={duration_sec-0.5:.2f}:d=0.5",
            "-ar", "48000", "-ac", "2", out_audio_path
        ]
        subprocess.run(fallback_cmd, capture_output=True, check=True)

    print(f"[hf-audio] Audio master complete: {os.path.getsize(out_audio_path)} bytes")
    return out_audio_path


def build_hyperframes_project(project_dir, script, audio_path, duration_sec=30.0):
    """Scaffolds and builds the complete HyperFrames project ready for rendering."""
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
    os.makedirs(project_dir)

    assets_dir = os.path.join(project_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Copy master audio to assets
    dest_audio = os.path.join(assets_dir, "audio.mp3")
    shutil.copy(audio_path, dest_audio)

    # Copy bundled gsap.min.js to assets if available
    local_gsap = os.path.join(ROOT, "assets", "gsap.min.js")
    if os.path.exists(local_gsap):
        shutil.copy(local_gsap, os.path.join(assets_dir, "gsap.min.js"))

    # Write hyperframes.json configuration
    hf_config = {
        "name": script.get("title_en", "rhyme-short"),
        "version": "1.0.0",
        "resolution": "portrait",
        "fps": 30,
        "width": 1080,
        "height": 1920
    }
    with open(os.path.join(project_dir, "hyperframes.json"), "w", encoding="utf-8") as f:
        json.dump(hf_config, f, indent=2)

    # Generate master index.html
    html = generate_hf_html(script, "assets/audio.mp3", duration_sec=duration_sec)
    with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    return project_dir


def render_hyperframes_video(project_dir, output_mp4, fps=30):
    """Runs `npx hyperframes render` to compile the animated HTML to 1080x1920 MP4."""
    npx_bin = shutil.which("npx") or "npx"
    if os.name == "nt" and not npx_bin.lower().endswith((".cmd", ".exe", ".bat")):
        npx_bin += ".cmd"
    cmd = [npx_bin, "hyperframes", "render", "-o", os.path.abspath(output_mp4), f"--fps={fps}"]
    log = f"[hf-render] Rendering {project_dir} -> {output_mp4}..."
    print(log)
    run_env = dict(os.environ)
    run_env["CHROME_FLAGS"] = "--no-sandbox --disable-setuid-sandbox"
    run_env["PUPPETEER_ARGS"] = "--no-sandbox --disable-setuid-sandbox"
    p = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=600, env=run_env)
    if p.returncode != 0:
        raise RuntimeError(f"HyperFrames render failed: {p.stderr}\n{p.stdout}")
    print(f"[hf-render] Success! Rendered: {output_mp4} (size: {os.path.getsize(output_mp4)} bytes)")
    return output_mp4


def extract_thumbnails(video_path, out_thumb_a, out_thumb_b, text_hi="जादुई बस!", text_en="MAGIC BUS!"):
    """Extracts crystal-clear frames from the rendered vector animation and overlays sticker badges."""
    # Frame A at 5.5s (Chintu jumping), Frame B at 16.5s (1-2-3 Counting & Mithu)
    from PIL import Image, ImageDraw, ImageFont
    import render

    os.makedirs(os.path.dirname(os.path.abspath(out_thumb_a)), exist_ok=True)
    raw_a = out_thumb_a + ".raw.jpg"
    raw_b = out_thumb_b + ".raw.jpg"

    subprocess.run(["ffmpeg", "-y", "-ss", "5.5", "-i", video_path, "-frames:v", "1", "-q:v", "2", raw_a],
                   capture_output=True, check=True)
    subprocess.run(["ffmpeg", "-y", "-ss", "16.5", "-i", video_path, "-frames:v", "1", "-q:v", "2", raw_b],
                   capture_output=True, check=True)

    # Use render.thumbnail to apply high-CTR sticker badge
    render.thumbnail(raw_a, text_hi, out_thumb_a, "A", size=(1080, 1920))
    render.thumbnail(raw_b, text_en, out_thumb_b, "B", size=(1080, 1920))

    for p in (raw_a, raw_b):
        if os.path.exists(p):
            os.remove(p)
    return out_thumb_a, out_thumb_b
