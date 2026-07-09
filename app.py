from __future__ import annotations

from html import escape

import streamlit as st

from downloader import (
    AUDIO_DIR,
    OUTPUT_DIR,
    VIDEO_DIR,
    detected_workers,
    download_media,
    extract_video_id,
    find_existing_downloads,
    format_total_downloaded_gb,
    read_download_history,
    thumbnail_url,
)


QUALITY_CHOICES = ["480p", "720p", "1080p"]
MEDIA_CHOICES = ["Video MP4", "Audio MP3"]

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="download",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def theme_tokens(theme: str) -> dict[str, str]:
    if theme == "Light":
        return {
            "page": "#eef2f7",
            "page_2": "#fff1f7",
            "ink": "#0f172a",
            "muted": "#6b6475",
            "panel": "rgba(255, 255, 255, 0.78)",
            "panel_solid": "#ffffff",
            "line": "rgba(219, 39, 119, 0.18)",
            "input": "rgba(255, 255, 255, 0.92)",
            "accent": "#ec4899",
            "accent_2": "#f472b6",
            "accent_3": "#8b5cf6",
            "success": "#16a34a",
            "danger_bg": "#fee2e2",
            "danger_text": "#991b1b",
            "shadow": "0 28px 80px rgba(15, 23, 42, 0.14)",
            "glow": "0 0 70px rgba(0, 122, 255, 0.20)",
        }
    return {
        "page": "#05070d",
        "page_2": "#1f1020",
        "ink": "#f8fafc",
        "muted": "#c7b4c2",
        "panel": "rgba(15, 23, 42, 0.68)",
        "panel_solid": "#111827",
        "line": "rgba(244, 114, 182, 0.18)",
        "input": "rgba(2, 6, 23, 0.74)",
        "accent": "#f472b6",
        "accent_2": "#fb7185",
        "accent_3": "#a78bfa",
        "success": "#22c55e",
        "danger_bg": "rgba(127, 29, 29, 0.45)",
        "danger_text": "#fecaca",
        "shadow": "0 34px 90px rgba(0, 0, 0, 0.42)",
        "glow": "0 0 90px rgba(56, 189, 248, 0.22)",
    }


def inject_styles(theme: str) -> None:
    tokens = theme_tokens(theme)
    st.markdown(
        f"""
        <style>
        :root {{
            --page: {tokens["page"]};
            --page-2: {tokens["page_2"]};
            --ink: {tokens["ink"]};
            --muted: {tokens["muted"]};
            --panel: {tokens["panel"]};
            --panel-solid: {tokens["panel_solid"]};
            --line: {tokens["line"]};
            --input: {tokens["input"]};
            --accent: {tokens["accent"]};
            --accent-2: {tokens["accent_2"]};
            --accent-3: {tokens["accent_3"]};
            --success: {tokens["success"]};
            --danger-bg: {tokens["danger_bg"]};
            --danger-text: {tokens["danger_text"]};
            --shadow: {tokens["shadow"]};
            --glow: 0 0 90px color-mix(in srgb, var(--accent) 24%, transparent);
        }}

        .stApp {{
            background:
                radial-gradient(circle at 15% 8%, color-mix(in srgb, var(--accent) 23%, transparent), transparent 31rem),
                radial-gradient(circle at 85% 2%, color-mix(in srgb, var(--accent-3) 20%, transparent), transparent 28rem),
                linear-gradient(145deg, var(--page), var(--page-2));
            color: var(--ink);
        }}

        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stToolbarActions"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"],
        div[data-testid="stDeployButton"],
        .stDeployButton,
        button[title="Deploy"],
        button[aria-label="Deploy"],
        #MainMenu,
        footer {{
            display: none !important;
        }}

        .block-container {{
            max-width: 1120px;
            padding: 22px 22px 46px;
        }}

        h1, h2, h3, p, label, span, div {{
            letter-spacing: 0 !important;
        }}

        .topbar {{
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 22px;
        }}

        .brand-pill {{
            align-items: center;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 999px;
            box-shadow: var(--shadow);
            color: var(--ink);
            display: inline-flex;
            font-size: 0.9rem;
            font-weight: 850;
            gap: 10px;
            padding: 10px 14px;
        }}

        .brand-dot {{
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            border-radius: 999px;
            box-shadow: var(--glow);
            display: inline-block;
            height: 12px;
            width: 12px;
        }}

        .total-pill {{
            align-items: center;
            background: linear-gradient(145deg, color-mix(in srgb, var(--panel-solid) 68%, transparent), var(--panel));
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: var(--shadow);
            color: var(--ink);
            display: inline-flex;
            flex-direction: column;
            justify-content: center;
            line-height: 1.05;
            margin-left: auto;
            min-height: 48px;
            min-width: 150px;
            padding: 8px 14px;
            text-align: center;
        }}

        div[data-testid="stElementContainer"]:has(.total-pill),
        div[data-testid="stMarkdown"]:has(.total-pill),
        div[data-testid="stMarkdownContainer"]:has(.total-pill) {{
            display: flex !important;
            justify-content: flex-end !important;
            width: 100% !important;
        }}

        .total-pill b {{
            color: var(--muted);
            display: block;
            font-size: 0.68rem;
            font-weight: 850;
            text-transform: uppercase;
        }}

        .total-pill span {{
            color: var(--ink);
            display: block;
            font-size: 1rem;
            font-weight: 950;
            margin-top: 3px;
            white-space: nowrap;
        }}

        @media (min-width: 761px) {{
            div[data-testid="stHorizontalBlock"]:has(.brand-pill) {{
                align-items: center !important;
                display: grid !important;
                gap: 22px !important;
                grid-template-columns: minmax(0, 1fr) 150px 58px !important;
                margin-bottom: 18px !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) > div[data-testid="stColumn"] {{
                width: auto !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) .stButton > button {{
                height: 48px !important;
                min-height: 48px !important;
                transform: translateY(8px);
                width: 58px !important;
            }}
        }}

        .hero {{
            background: linear-gradient(145deg, color-mix(in srgb, var(--panel-solid) 72%, transparent), var(--panel));
            border: 1px solid var(--line);
            border-radius: 8px;
            margin-bottom: 22px;
            box-shadow: var(--shadow);
            overflow: hidden;
            padding: clamp(18px, 4vw, 34px);
            position: relative;
        }}

        .hero::after {{
            background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 30%, transparent), color-mix(in srgb, var(--accent-3) 20%, transparent));
            content: "";
            filter: blur(38px);
            height: 190px;
            opacity: 0.72;
            position: absolute;
            right: -70px;
            top: -78px;
            width: 270px;
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
        }}

        .eyebrow {{
            color: var(--accent-2);
            font-size: 0.82rem;
            font-weight: 900;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}

        .hero h1 {{
            color: var(--ink);
            font-size: clamp(2.2rem, 5vw, 4.8rem);
            line-height: 0.96;
            margin: 0;
            max-width: 860px;
        }}

        .hero p {{
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.65;
            margin: 18px 0 0;
            max-width: 720px;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 18px 0 24px;
        }}

        .stat {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: var(--shadow);
            min-height: 94px;
            padding: 18px;
        }}

        .stat b {{
            color: var(--muted);
            display: block;
            font-size: 0.8rem;
            font-weight: 750;
            margin-bottom: 8px;
        }}

        .stat span {{
            color: var(--ink);
            display: block;
            font-size: clamp(1rem, 2vw, 1.22rem);
            font-weight: 950;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }}

        div[data-testid="stForm"] {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: var(--shadow);
            padding: 24px;
        }}

        .panel-title {{
            color: var(--ink);
            font-size: 1.32rem;
            font-weight: 950;
            margin-bottom: 6px;
        }}

        .panel-copy {{
            color: var(--muted);
            margin-bottom: 18px;
        }}

        div[data-testid="stTextInput"] label p,
        div[data-testid="stButtonGroup"] label p,
        div[data-testid="stSegmentedControl"] label p,
        div[data-testid="stCheckbox"] label p {{
            color: var(--ink) !important;
            font-size: 0.94rem !important;
            font-weight: 850 !important;
        }}

        div[data-testid="stTextInput"] input {{
            background: var(--input) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08) !important;
            color: var(--ink) !important;
            caret-color: var(--accent) !important;
            font-size: 1.04rem !important;
            font-weight: 700 !important;
            min-height: 60px !important;
            padding: 0 16px !important;
        }}

        div[data-testid="stTextInput"] input::placeholder {{
            color: var(--muted) !important;
            opacity: 0.88 !important;
            font-weight: 550 !important;
        }}

        div[data-testid="stTextInput"] input:focus {{
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent), var(--glow) !important;
        }}

        div[data-testid="stButtonGroup"] div[role="radiogroup"],
        div[data-testid="stSegmentedControl"] div[role="radiogroup"] {{
            background: var(--input) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08) !important;
            display: flex !important;
            gap: 8px !important;
            padding: 8px !important;
            width: 100% !important;
        }}

        div[data-testid="stButtonGroup"] [role="radio"],
        div[data-testid="stSegmentedControl"] [role="radio"] {{
            background: color-mix(in srgb, var(--panel-solid) 84%, transparent) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px !important;
            color: var(--ink) !important;
            min-height: 46px !important;
        }}

        div[data-testid="stButtonGroup"] [role="radio"][aria-checked="true"],
        div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] {{
            background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
            border-color: transparent !important;
            box-shadow: 0 12px 28px color-mix(in srgb, var(--accent) 22%, transparent) !important;
            color: #ffffff !important;
        }}

        div[data-testid="stButtonGroup"] [role="radio"][aria-checked="true"] *,
        div[data-testid="stSegmentedControl"] [role="radio"][aria-checked="true"] * {{
            color: #ffffff !important;
        }}

        div[data-testid="stButtonGroup"] label,
        div[data-testid="stSegmentedControl"] label {{
            background: color-mix(in srgb, var(--panel-solid) 76%, transparent) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px !important;
            color: var(--ink) !important;
            flex: 1 1 0 !important;
            justify-content: center !important;
            min-height: 46px !important;
            padding: 8px 12px !important;
        }}

        div[data-testid="stButtonGroup"] label *,
        div[data-testid="stSegmentedControl"] label * {{
            color: var(--ink) !important;
            font-weight: 850 !important;
        }}

        div[data-testid="stButtonGroup"] label:has(input:checked),
        div[data-testid="stButtonGroup"] label[aria-checked="true"],
        div[data-testid="stSegmentedControl"] label:has(input:checked),
        div[data-testid="stSegmentedControl"] label[aria-checked="true"] {{
            background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
            border-color: transparent !important;
            box-shadow: 0 12px 28px color-mix(in srgb, var(--accent) 22%, transparent) !important;
        }}

        div[data-testid="stButtonGroup"] label:has(input:checked) *,
        div[data-testid="stButtonGroup"] label[aria-checked="true"] *,
        div[data-testid="stSegmentedControl"] label:has(input:checked) *,
        div[data-testid="stSegmentedControl"] label[aria-checked="true"] * {{
            color: #ffffff !important;
        }}

        div[data-testid="stCheckbox"] {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 9px 13px;
        }}

        div[data-testid="stCheckbox"] * {{
            color: var(--ink) !important;
            font-weight: 800 !important;
        }}

        div[data-testid="stFormSubmitButton"],
        div[data-testid="stFormSubmitButton"] div {{
            width: 100% !important;
        }}

        div[data-testid="stFormSubmitButton"] button,
        button[kind="primaryFormSubmit"] {{
            background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
            border: 0 !important;
            border-radius: 8px !important;
            box-shadow: 0 18px 36px color-mix(in srgb, var(--accent) 28%, transparent) !important;
            color: #ffffff !important;
            font-size: 1.02rem !important;
            font-weight: 950 !important;
            min-height: 58px !important;
            width: 100% !important;
        }}

        div[data-testid="stFormSubmitButton"] button *,
        button[kind="primaryFormSubmit"] * {{
            color: #ffffff !important;
            font-weight: 950 !important;
        }}

        div[data-testid="stFormSubmitButton"] button:hover,
        button[kind="primaryFormSubmit"]:hover {{
            filter: brightness(1.06);
            color: #ffffff !important;
        }}

        .stButton > button {{
            background: var(--panel) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px !important;
            box-shadow: var(--shadow) !important;
            color: var(--accent) !important;
            font-size: 1.55rem !important;
            font-weight: 950 !important;
            height: 48px !important;
            min-height: 48px !important;
            padding: 0 !important;
            width: 58px !important;
        }}

        .stButton > button:hover {{
            border-color: var(--accent) !important;
            color: var(--accent-2) !important;
        }}

        div[data-testid="stFormSubmitButton"] button,
        button[kind="primaryFormSubmit"] {{
            background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
            border: 0 !important;
            border-radius: 8px !important;
            box-shadow: 0 18px 36px color-mix(in srgb, var(--accent) 28%, transparent) !important;
            color: #ffffff !important;
            font-size: 1.02rem !important;
            font-weight: 950 !important;
            min-height: 58px !important;
            width: 100% !important;
        }}

        .progress-card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: var(--shadow);
            margin-top: 18px;
            padding: 20px;
        }}

        .progress-top {{
            align-items: flex-start;
            display: flex;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 12px;
        }}

        .progress-title {{
            color: var(--ink);
            font-size: 1rem;
            font-weight: 950;
        }}

        .progress-meta {{
            color: var(--muted);
            font-size: 0.9rem;
            font-weight: 750;
            text-align: right;
        }}

        .progress-percent {{
            color: var(--ink);
            display: block;
            font-size: 1.75rem;
            font-weight: 950;
            line-height: 1;
            margin-bottom: 6px;
        }}

        .meter {{
            background: color-mix(in srgb, var(--muted) 18%, transparent);
            border-radius: 999px;
            height: 14px;
            overflow: hidden;
        }}

        .meter-fill {{
            background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent-3));
            border-radius: 999px;
            box-shadow: var(--glow);
            height: 100%;
            min-width: 8px;
            transition: width 260ms ease;
        }}

        .success-card,
        .error-card {{
            border-radius: 8px;
            font-weight: 850;
            margin-top: 18px;
            padding: 16px 18px;
        }}

        .success-card {{
            background: color-mix(in srgb, var(--success) 20%, transparent);
            border: 1px solid color-mix(in srgb, var(--success) 34%, transparent);
            color: var(--ink);
        }}

        .error-card {{
            background: var(--danger-bg);
            border: 1px solid color-mix(in srgb, var(--danger-text) 22%, transparent);
            color: var(--danger-text);
        }}

        .file-row {{
            align-items: center;
            border-top: 1px solid var(--line);
            background: color-mix(in srgb, var(--panel-solid) 28%, transparent);
            border: 1px solid var(--line);
            border-radius: 8px;
            color: var(--ink);
            display: grid;
            grid-template-columns: 168px minmax(0, 1fr) auto;
            gap: 12px;
            margin-bottom: 12px;
            overflow: hidden;
            padding: 10px;
        }}

        .file-thumb {{
            aspect-ratio: 16 / 9;
            background: color-mix(in srgb, var(--muted) 20%, transparent);
            border-radius: 6px;
            object-fit: cover !important;
            display: block;
            height: 100% !important;
            width: 100% !important;
        }}

        .file-name {{
            font-weight: 850;
            overflow-wrap: anywhere;
        }}

        .file-meta {{
            align-self: center;
            min-width: 0;
        }}

        .file-size {{
            color: var(--muted);
            flex: 0 0 auto;
            font-weight: 800;
            justify-self: end;
            white-space: nowrap;
        }}

        .mode-badge {{
            color: var(--accent);
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 950;
            margin-top: 6px;
            text-transform: uppercase;
        }}

        .duplicate-card {{
            background: color-mix(in srgb, #f59e0b 18%, transparent);
            border: 1px solid color-mix(in srgb, #f59e0b 38%, transparent);
            border-radius: 8px;
            color: var(--ink);
            font-weight: 800;
            margin-top: 18px;
            padding: 16px 18px;
        }}

        code {{
            overflow-wrap: anywhere !important;
            white-space: pre-wrap !important;
        }}

        @media (max-width: 760px) {{
            .block-container {{
                padding-left: 16px;
                padding-right: 16px;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) {{
                align-items: center;
                display: flex !important;
                flex-direction: row !important;
                gap: 12px !important;
                justify-content: space-between !important;
                margin-bottom: 18px !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) > div[data-testid="stColumn"] {{
                align-items: center !important;
                display: flex !important;
                flex: 0 0 auto !important;
                min-width: 0 !important;
                width: auto !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) > div[data-testid="stColumn"]:first-child {{
                flex: 1 1 auto !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) .brand-pill {{
                font-size: 0.84rem;
                height: 40px;
                padding: 9px 13px;
                transform: translateY(-8px);
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) .total-pill {{
                min-height: 42px;
                min-width: 116px;
                padding: 7px 10px;
                transform: translateY(-8px);
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) .total-pill b {{
                font-size: 0.56rem;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) .total-pill span {{
                font-size: 0.88rem;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) div[data-testid="stElementContainer"],
            div[data-testid="stHorizontalBlock"]:has(.brand-pill) div[data-testid="stMarkdown"],
            div[data-testid="stHorizontalBlock"]:has(.brand-pill) div[data-testid="stMarkdownContainer"] {{
                align-items: center !important;
                display: flex !important;
                height: 46px !important;
            }}

            div[data-testid="stHorizontalBlock"]:has(.brand-pill) .stButton > button {{
                height: 46px !important;
                min-height: 46px !important;
                width: 52px !important;
            }}

            .stats {{
                grid-template-columns: 1fr;
            }}

            .hero {{
                padding: 18px;
            }}

            .hero h1 {{
                font-size: 2.4rem;
            }}

            div[data-testid="stForm"] {{
                padding: 14px;
            }}

            .progress-top {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .progress-meta {{
                text-align: left;
            }}

            .file-row {{
                grid-template-columns: 104px minmax(0, 1fr);
            }}

            .file-size {{
                grid-column: 2;
                justify-self: start;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def progress_markup(
    percent: float,
    status: str,
    speed: str,
    eta: str,
    downloaded: str = "unknown size",
    total: str = "unknown size",
) -> str:
    clean_percent = min(100.0, max(0.0, percent * 100))
    size_text = f"{downloaded} / {total}"
    return f"""
    <div class="progress-card">
        <div class="progress-top">
            <div class="progress-title">{escape(status)}</div>
            <div class="progress-meta">
                <span class="progress-percent">{clean_percent:.1f}%</span>
                {escape(size_text)}<br>
                {escape(speed)} | ETA {escape(eta)}
            </div>
        </div>
        <div class="meter"><div class="meter-fill" style="width: {clean_percent:.1f}%"></div></div>
    </div>
    """


def total_downloaded_label() -> str:
    history = read_download_history()
    return format_total_downloaded_gb(history.get("total_bytes", 0))


def total_downloaded_markup() -> str:
    return f"""
    <div class="total-pill">
        <b>Total downloads</b>
        <span>{escape(total_downloaded_label())}</span>
    </div>
    """


def render_header() -> None:
    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-content">
                <div class="eyebrow">Private local downloader</div>
                <h1>YouTube Downloader</h1>
                <p>Paste a link, choose video or MP3, and save it directly on this computer.</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_features() -> None:
    st.markdown(
        f"""
        <section class="stats">
            <div class="stat"><b>Video folder</b><span>{VIDEO_DIR}</span></div>
            <div class="stat"><b>Audio folder</b><span>{AUDIO_DIR}</span></div>
            <div class="stat"><b>Slow internet mode</b><span>50 retries, 120s timeout</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def recent_files() -> list:
    folders = [VIDEO_DIR, AUDIO_DIR, OUTPUT_DIR]
    seen: set[str] = set()
    files = []
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".mp3"}:
                key = str(path.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    files.append(path)
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:8]


def render_recent_files() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    files = recent_files()
    if not files:
        return

    st.subheader("Recent downloads")
    for path in files:
        size_mb = path.stat().st_size / (1024 * 1024)
        video_id = extract_video_id(path.name)
        thumb = thumbnail_url(video_id)
        fallback_thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
        mode_label = "MP3 audio" if path.suffix.lower() == ".mp3" else "Video"
        img = (
            f'<img class="file-thumb" src="{escape(thumb)}" alt="Video thumbnail" loading="lazy" onerror="this.onerror=null;this.src=\'{escape(fallback_thumb)}\';">'
            if thumb
            else '<div class="file-thumb"></div>'
        )
        st.markdown(
            f"""
            <div class="file-row">
                {img}
                <div class="file-meta">
                    <div class="file-name">{escape(path.name)}</div>
                    <span class="mode-badge">{escape(mode_label)}</span>
                </div>
                <div class="file-size">{size_mb:.1f} MB</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_bottom_sections(target) -> None:
    with target.container():
        st.divider()
        render_recent_files()
        render_features()
        st.caption(
            "Only download videos you own, have permission to download, or are allowed to save."
        )


def main() -> None:
    if "theme_name" not in st.session_state:
        st.session_state.theme_name = "Dark"
    params = st.query_params
    query_url = params.get("url", "")
    query_quality = params.get("quality", "720p")
    query_mode = params.get("mode", "video")
    query_auto = params.get("auto", "0") == "1"

    query_download_key = f"{query_mode}:{query_quality}:{query_url}" if query_url else ""
    should_apply_query = bool(
        query_url
        and st.session_state.get("applied_query_download_key") != query_download_key
    )
    if should_apply_query:
        st.session_state.applied_query_download_key = query_download_key
        st.session_state.youtube_url = query_url
        if query_quality in QUALITY_CHOICES:
            st.session_state.quality = query_quality
        if query_mode in {"audio", "video"}:
            st.session_state.media_choice = "Audio MP3" if query_mode == "audio" else "Video MP4"

    if "quality" not in st.session_state:
        st.session_state.quality = "720p"
    if "media_choice" not in st.session_state:
        st.session_state.media_choice = "Video MP4"

    theme = st.session_state.theme_name
    inject_styles(theme)

    top_left, top_stat, top_right = st.columns([1, 0.44, 0.16], vertical_alignment="center")
    with top_left:
        st.markdown(
            '<div class="brand-pill"><span class="brand-dot"></span>YTD Studio</div>',
            unsafe_allow_html=True,
        )
    with top_stat:
        st.markdown(total_downloaded_markup(), unsafe_allow_html=True)
    with top_right:
        toggle_label = "◐" if st.session_state.theme_name == "Dark" else "◑"
        with st.container(horizontal_alignment="right"):
            if st.button(toggle_label, width="content"):
                st.session_state.theme_name = "Light" if st.session_state.theme_name == "Dark" else "Dark"
                st.rerun()

    render_header()

    with st.form("download_form", clear_on_submit=False):
        st.markdown(
            """
            <div class="panel-title">Download</div>
            <div class="panel-copy">Paste a YouTube URL, choose MP4 video or MP3 audio, then start.</div>
            """,
            unsafe_allow_html=True,
        )
        url = st.text_input(
            "YouTube link",
            key="youtube_url",
            placeholder="https://www.youtube.com/watch?v=...",
        )
        selected_media = st.segmented_control(
            "Download type",
            MEDIA_CHOICES,
            key="media_choice",
            required=True,
            width="stretch",
        )
        selected_quality = st.segmented_control(
            "Video quality (MP4 only)",
            QUALITY_CHOICES,
            key="quality",
            required=True,
            width="stretch",
        )
        allow_redownload = st.checkbox(
            "Download again even if this video already exists",
            value=False,
            key="allow_redownload",
        )
        submitted = st.form_submit_button(
            "Start download",
            type="primary",
            width="stretch",
        )

    progress_placeholder = st.empty()
    result_placeholder = st.empty()
    detail = st.empty()
    bottom_placeholder = st.empty()
    render_bottom_sections(bottom_placeholder)

    should_auto_download = (
        query_auto
        and query_url
        and st.session_state.get("auto_download_key") != query_download_key
    )
    if should_auto_download:
        st.session_state.auto_download_key = query_download_key
        submitted = True

    if submitted:
        video_id = extract_video_id(url)
        media_mode = "audio" if selected_media == "Audio MP3" else "video"
        existing_files = find_existing_downloads(video_id, media_mode=media_mode)
        if existing_files and not allow_redownload:
            existing_list = "<br>".join(escape(str(file)) for file in existing_files[:3])
            result_placeholder.markdown(
                f"""
                <div class="duplicate-card">
                    This {escape(selected_media)} download is already in your downloads folder.<br>
                    {existing_list}<br><br>
                    Tick "Download again even if this video already exists" if you want another copy.
                </div>
                """,
                unsafe_allow_html=True,
            )
            if should_auto_download:
                st.query_params.clear()
        else:
            progress_placeholder.markdown(
                progress_markup(
                    0,
                    "Preparing download",
                    "Checking connection",
                    "calculating",
                ),
                unsafe_allow_html=True,
            )

            def update_progress(info: dict) -> None:
                if info["status"] == "downloading":
                    percent = info["percent"]
                    speed = info["speed"] or "slow connection, still working"
                    eta = info["eta"] or "unknown"
                    downloaded = info.get("downloaded") or "unknown size"
                    total = info.get("total") or "unknown size"
                    progress_placeholder.markdown(
                        progress_markup(
                            percent,
                            "Downloading",
                            speed,
                            eta,
                            downloaded,
                            total,
                        ),
                        unsafe_allow_html=True,
                    )
                elif info["status"] == "finished":
                    progress_placeholder.markdown(
                        progress_markup(
                            1.0,
                            "Download finished",
                            "Merging MP4",
                            "almost done",
                        ),
                        unsafe_allow_html=True,
                    )

            result = download_media(
                url,
                workers=detected_workers(),
                quality=selected_quality,
                media_mode=media_mode,
                progress_callback=update_progress,
                allow_redownload=allow_redownload,
            )

            if result.ok:
                progress_placeholder.markdown(
                    progress_markup(1.0, "Complete", selected_media, "done"),
                    unsafe_allow_html=True,
                )
                saved_files = "<br>".join(escape(str(file)) for file in result.files)
                result_placeholder.markdown(
                    f'<div class="success-card">Download complete.<br>{saved_files}</div>',
                    unsafe_allow_html=True,
                )
                bottom_placeholder.empty()
                render_bottom_sections(bottom_placeholder)
            else:
                progress_placeholder.empty()
                result_placeholder.markdown(
                    f'<div class="error-card">{escape(result.message)}</div>',
                    unsafe_allow_html=True,
                )
                if result.details:
                    detail.code(result.details)
            if should_auto_download:
                st.query_params.clear()


if __name__ == "__main__":
    main()
