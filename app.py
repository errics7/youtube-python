import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────────
# KONFIGURASI HALAMAN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="YT Sheet Tracker",
    page_icon="🎬",
    layout="wide",
)

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {
    --bg:      #F5F4F0;
    --surface: #FFFFFF;
    --surface2:#EEECEA;
    --border:  #D8D5CF;
    --accent:  #E8472A;
    --accent2: #2A6AE8;
    --text:    #1A1916;
    --muted:   #7A776F;
    --green:   #16A34A;
    --radius:  12px;
    --shadow:  0 2px 12px rgba(0,0,0,0.08);
}

/* ── Background & font ── */
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg) !important; }
p, div, label, input, textarea, select, h1, h2, h3, h4, h5, h6 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text);
}

/* ── Sembunyikan sidebar bawaan Streamlit sepenuhnya ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display: none !important;
}

/* ── NAVBAR custom ── */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 32px;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 999;
    box-shadow: 0 1px 8px rgba(0,0,0,0.06);
    margin-bottom: 32px;
}
.navbar-brand {
    font-weight: 700;
    font-size: 16px;
    color: var(--text) !important;
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
}
.navbar-links {
    display: flex;
    align-items: center;
    gap: 4px;
}
.navbar-link {
    padding: 6px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: var(--muted) !important;
    text-decoration: none;
    cursor: pointer;
    border: none;
    background: transparent;
    transition: all .15s ease;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.navbar-link:hover {
    background: var(--surface2);
    color: var(--text) !important;
}
.navbar-link.active {
    background: var(--text);
    color: #ffffff !important;
    font-weight: 600;
}
.navbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
}
.navbar-sheets-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 16px;
    background: var(--green);
    color: #ffffff !important;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    border: 2px solid var(--green);
    transition: background .15s, color .15s;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.navbar-sheets-btn:hover {
    background: #ffffff;
    color: var(--green) !important;
}

/* ── Label widget ── */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
    color: var(--text) !important;
    font-weight: 600 !important;
}

/* ── Caption ── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--muted) !important;
}

/* ── Tombol primary ── */
.stButton > button {
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    transition: all .18s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.25) !important;
    filter: brightness(1.08) !important;
}

/* ── Tombol secondary (Hapus Semua) ── */
.stButton > button[kind="secondary"] {
    color: var(--text) !important;
    background-color: var(--surface2) !important;
    border: 1.5px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: var(--border) !important;
    filter: none !important;
}

/* ── Select box ── */
[data-baseweb="select"] > div {
    background-color: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="select"] p {
    color: var(--text) !important;
    background-color: transparent !important;
}
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] [role="option"] * {
    color: var(--text) !important;
    background-color: var(--surface) !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"]:hover * {
    background-color: var(--surface2) !important;
}
[data-baseweb="popover"] [aria-selected="true"],
[data-baseweb="popover"] [aria-selected="true"] * {
    background-color: #DBEAFE !important;
    color: #1D4ED8 !important;
}

/* ── Text area & text input ── */
.stTextArea textarea, .stTextInput input {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent2) !important;
    box-shadow: 0 0 0 3px rgba(42,106,232,.12) !important;
}

/* ── Date input ── */
.stDateInput > div > div, .stDateInput input {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Kartu preview video ── */
.yt-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 8px;
    box-shadow: var(--shadow);
    transition: box-shadow .18s;
}
.yt-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,.12); }
.yt-card-num {
    font-size: 10px; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase;
    color: var(--accent) !important;
    font-family: 'DM Mono', monospace;
}
.yt-card-title { font-weight: 600; font-size: 14px; color: var(--text) !important; margin: 4px 0; }
.yt-card-meta  { font-size: 12px; color: var(--muted) !important; font-family: 'DM Mono', monospace; }
.yt-card-type  {
    display: inline-block; font-size: 10px; font-weight: 700;
    letter-spacing: .05em; padding: 2px 8px; border-radius: 20px; margin-top: 4px;
}
.badge-short { background: #FEE2E2; color: #B91C1C !important; }
.badge-vod   { background: #DBEAFE; color: #1D4ED8 !important; }

/* ── Kotak peringatan ── */
.warn-box {
    background: #FEF9EC; border: 1.5px solid #F59E0B;
    border-radius: 8px; padding: 10px 14px;
    font-size: 13px; margin-bottom: 8px;
}
.warn-box, .warn-box * { color: #92400E !important; }

/* ── Page header ── */
.page-header { display:flex; align-items:center; gap:12px; margin-bottom:24px; }
.page-header-icon { font-size: 36px; line-height: 1; }
.page-header-title { font-size: 26px; font-weight: 700; color: var(--text) !important; margin:0; }
.page-header-sub   { font-size: 13px; color: var(--muted) !important; margin:0; }

/* ── Label section ── */
.section-label {
    font-size: 11px; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: var(--muted) !important; margin-bottom: 8px;
}

/* ── Kurangi padding konten utama karena tidak ada sidebar ── */
[data-testid="stMainBlockContainer"] {
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KONSTANTA
# ─────────────────────────────────────────────
SPREADSHEET_ID = "1BrvBpYU7yr1Vcvoeqae70B1Nywsv5wGM8ZLF6hDQgGA"
SHEETS_URL     = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
MAX_LINKS      = 15

# Urutan kolom sesuai Sheets (dari gambar): Tanggal | Editor | Judul | Link | Views | Keterangan
HEADERS_VOD   = ["Tanggal", "Editor", "Judul", "Link", "Views", "Keterangan"]
HEADERS_SHORT = ["Tanggal", "Editor", "Judul", "Link", "Views", "Keterangan"]


# ─────────────────────────────────────────────
# INISIALISASI GOOGLE API
# ─────────────────────────────────────────────
@st.cache_resource
def init_google_clients():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds       = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    gc          = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    youtube     = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])
    return spreadsheet, youtube

spreadsheet, youtube = init_google_clients()


# ─────────────────────────────────────────────
# FUNGSI UTILITAS
# ─────────────────────────────────────────────
def get_video_id(url: str):
    """Ekstrak video ID dari berbagai format URL YouTube."""
    shorts_match = re.search(r'shorts/([a-zA-Z0-9_-]{11})', url)
    if shorts_match:
        return shorts_match.group(1)
    yt_match = re.search(r'(?:v=|youtu\.be/|embed/|watch\?v=)([^&"?\s]{11})', url)
    if yt_match:
        return yt_match.group(1)
    parsed = urlparse(url)
    if parsed.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if 'v' in parse_qs(parsed.query):
            return parse_qs(parsed.query)['v'][0]
    elif parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    return None


def format_date(published: str) -> str:
    """Format ISO datetime ke DD-MM-YYYY."""
    try:
        return datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").strftime("%d-%m-%Y")
    except Exception:
        return published


def extract_editor(description: str) -> str:
    """Ambil nama editor dari deskripsi video."""
    for line in description.split("\n"):
        if "editor video" in line.lower():
            parts = line.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
    return "Erricson Bernedy S"


def get_or_create_worksheet(name: str, headers: list):
    """Ambil worksheet; buat baru dengan header jika belum ada."""
    try:
        return spreadsheet.worksheet(name)
    except Exception:
        ws = spreadsheet.add_worksheet(name, 1000, 10)
        ws.append_row(headers)
        return ws


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "page"          not in st.session_state:
    st.session_state.page          = "input"
if "links_text"    not in st.session_state:
    st.session_state.links_text    = ""
if "preview_data"  not in st.session_state:
    st.session_state.preview_data  = []
if "clear_trigger" not in st.session_state:
    st.session_state.clear_trigger = 0


# ─────────────────────────────────────────────
# NAVBAR
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# NAVIGASI via URL query parameter
# Saat user klik tombol navbar, URL berubah → Streamlit rerun → halaman berganti
# ─────────────────────────────────────────────
params = st.query_params
if "page" in params:
    st.session_state.page = params["page"]

active_input = "active" if st.session_state.page == "input" else ""
active_leave = "active" if st.session_state.page == "leave" else ""

st.markdown(f"""
<div class="navbar">
    <span class="navbar-brand">🎬 YT Sheet Tracker</span>
    <div class="navbar-links">
        <a class="navbar-link {active_input}" href="?page=input">📥 Input Video YouTube</a>
        <a class="navbar-link {active_leave}" href="?page=leave">🗓️ Libur &amp; Cuti</a>
    </div>
    <div class="navbar-right">
        <a href="{SHEETS_URL}" target="_blank" class="navbar-sheets-btn">
            📊 Buka Google Sheets
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# HALAMAN 1 – INPUT VIDEO YOUTUBE
# ═══════════════════════════════════════════════════════════════════
if st.session_state.page == "input":

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">📥</div>
        <div>
            <div class="page-header-title">Input Video YouTube</div>
            <div class="page-header-sub">Rekam data video ke Google Sheets secara otomatis</div>
            <div style="font-size:11px;color:#7A776F;margin-top:2px">Maksimal 15 link per sesi</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Masukkan Link YouTube</div>', unsafe_allow_html=True)

    # ── TEXTBOX ───────────────────────────────────────────────────
    input_key  = f"links_input_{st.session_state.clear_trigger}"
    links_text = st.text_area(
        label="links_input",
        value=st.session_state.links_text,
        placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...\nhttps://www.youtube.com/shorts/...",
        height=220,
        label_visibility="collapsed",
        key=input_key,
    )
    st.session_state.links_text = links_text

    # ── PARSE & VALIDASI ──────────────────────────────────────────
    raw_lines     = [l.strip() for l in links_text.split("\n") if l.strip()]
    valid_links   = []
    invalid_lines = []

    for i, line in enumerate(raw_lines, 1):
        if get_video_id(line):
            valid_links.append((i, line))
        else:
            invalid_lines.append((i, line))

    if raw_lines:
        invalid_msg = (
            f"⚠️ <b>{len(invalid_lines)}</b> baris bukan link YouTube"
            if invalid_lines else "🎉 Semua baris valid"
        )
        st.markdown(
            f"<div style='font-size:13px;color:#7A776F'>"
            f"✅ <b>{len(valid_links)}</b> link valid &nbsp;|&nbsp; {invalid_msg}"
            f"</div>",
            unsafe_allow_html=True
        )

    if invalid_lines:
        warn_text = ", ".join([f"Baris {i}" for i, _ in invalid_lines])
        st.markdown(
            f'<div class="warn-box">⚠️ Baris berikut bukan link YouTube yang valid '
            f'dan akan dilewati: <b>{warn_text}</b></div>',
            unsafe_allow_html=True
        )

    if len(valid_links) > MAX_LINKS:
        st.error(f"❌ Maksimal {MAX_LINKS} link YouTube per pengiriman.")
        valid_links = valid_links[:MAX_LINKS]

    # ── TOMBOL ────────────────────────────────────────────────────
    col_send, col_clear = st.columns([3, 1])
    with col_send:
        btn_send  = st.button("▶️ Kirim ke Google Sheets", use_container_width=True, type="primary")
    with col_clear:
        btn_clear = st.button("🗑️ Hapus Semua", use_container_width=True)

    if btn_clear:
        st.session_state.links_text    = ""
        st.session_state.preview_data  = []
        st.session_state.clear_trigger += 1
        st.rerun()

    # ── PREVIEW OTOMATIS ──────────────────────────────────────────
    video_ids    = [get_video_id(url) for _, url in valid_links]
    original_map = {get_video_id(url): url for _, url in valid_links}

    prev_ids = {item["id"] for item in st.session_state.preview_data}
    curr_ids = set(vid for vid in video_ids if vid)

    if curr_ids and curr_ids != prev_ids:
        with st.spinner("Memuat preview video..."):
            resp = youtube.videos().list(
                part="snippet", id=",".join(list(curr_ids))
            ).execute()
            st.session_state.preview_data = resp.get("items", [])
    elif not curr_ids:
        st.session_state.preview_data = []

    # ── TAMPILKAN PREVIEW ─────────────────────────────────────────
    if st.session_state.preview_data:
        st.markdown("---")
        st.markdown('<div class="section-label">Preview Video</div>', unsafe_allow_html=True)

        items = st.session_state.preview_data
        for row_start in range(0, len(items), 3):
            cols = st.columns(3)
            for col_idx, item in enumerate(items[row_start:row_start + 3]):
                vid_id    = item["id"]
                title     = item["snippet"]["title"]
                published = item["snippet"]["publishedAt"]
                url       = original_map.get(vid_id, "")
                is_short  = "/shorts/" in url
                badge = (
                    '<span class="yt-card-type badge-short">SHORT</span>'
                    if is_short else
                    '<span class="yt-card-type badge-vod">VOD</span>'
                )
                num = row_start + col_idx + 1
                with cols[col_idx]:
                    st.markdown(f"""
                    <div class="yt-card">
                        <div class="yt-card-num">#{num}</div>
                        <div class="yt-card-title">{title}</div>
                        <div class="yt-card-meta">📅 {format_date(published)}</div>
                        {badge}
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"[🔗 Buka Video]({url})")

    # ── KIRIM KE GOOGLE SHEETS ─────────────────────────────────────
    if btn_send:
        if not video_ids:
            st.error("❌ Tidak ada link YouTube yang valid untuk dikirim.")
        else:
            ws_short = get_or_create_worksheet("SHORT", HEADERS_SHORT)
            ws_vod   = get_or_create_worksheet("VOD",   HEADERS_VOD)

            with st.spinner("Mengirim data ke Google Sheets..."):
                resp = youtube.videos().list(
                    part="snippet,statistics",
                    id=",".join(video_ids)
                ).execute()

            success_titles = []
            failed_ids     = []

            for item in resp.get("items", []):
                try:
                    vid_id    = item["id"]
                    title     = item["snippet"]["title"]
                    desc      = item["snippet"].get("description", "")
                    pub       = item["snippet"]["publishedAt"]
                    url       = original_map.get(vid_id, "")
                    editor    = extract_editor(desc)
                    views_int = int(item.get("statistics", {}).get("viewCount", "0"))

                    # Urutan kolom: Tanggal | Editor | Judul | Link | Views | Keterangan
                    row = [format_date(pub), editor, title, url, views_int, ""]

                    if "/shorts/" in url:
                        ws_short.append_row(row, value_input_option="USER_ENTERED")
                    else:
                        ws_vod.append_row(row, value_input_option="USER_ENTERED")

                    success_titles.append(title)
                except Exception as e:
                    failed_ids.append((vid_id, str(e)))

            if success_titles:
                st.success(f"🎉 Berhasil mengirim **{len(success_titles)}** video ke Google Sheets!")

            if failed_ids:
                for vid, err in failed_ids:
                    st.warning(f"⚠️ Gagal mengirim `{vid}`: {err}")
                failed_set = {v for v, _ in failed_ids}
                remaining  = "\n".join(
                    u for v, u in original_map.items() if v in failed_set
                )
                st.session_state.links_text   = remaining
                st.session_state.preview_data = []
            else:
                st.session_state.links_text    = ""
                st.session_state.preview_data  = []
                st.session_state.clear_trigger += 1

            st.rerun()


# ═══════════════════════════════════════════════════════════════════
# HALAMAN 2 – LIBUR & CUTI
# ═══════════════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">🗓️</div>
        <div>
            <div class="page-header-title">Entri Hari Libur & Cuti</div>
            <div class="page-header-sub">Catat ketidakhadiran editor ke Google Sheets</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_form, _ = st.columns([2, 1])

    with col_form:
        leave_date = st.date_input("📅 Tanggal")

        LEAVE_OPTIONS = ["Libur", "Cuti", "Izin", "Sakit", "Lainnya"]
        leave_type    = st.selectbox("📋 Jenis Kegiatan", LEAVE_OPTIONS)

        custom_activity = ""
        if leave_type == "Lainnya":
            custom_activity = st.text_input(
                "✏️ Isi Kegiatan *",
                placeholder="Contoh: Rapat, Perjalanan Dinas, dll."
            )

        editor = st.selectbox("👤 Editor", ["Erricson Bernedy S"])

        st.markdown("")
        btn_leave = st.button("💾 Simpan Entri", type="primary", use_container_width=True)

        st.markdown("""
        <div style="background:#EEF4FF;border:1px solid #BDD3FF;border-radius:10px;
                    padding:14px 16px;margin-top:16px">
            <div style="font-weight:700;font-size:13px;margin-bottom:4px;color:#1A1916">
                📌 Info
            </div>
            <div style="font-size:13px;color:#3D3D3D;line-height:1.7">
                Entri akan dicatat ke sheet <b>VOD</b> dan <b>SHORT</b> sekaligus,
                pada kolom <i>Keterangan</i>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── SIMPAN ────────────────────────────────────────────────────
    if btn_leave:
        if leave_type == "Lainnya":
            if not custom_activity.strip():
                st.error("❌ Kolom 'Isi Kegiatan' wajib diisi saat memilih Lainnya.")
                st.stop()
            keterangan = custom_activity.strip()
        else:
            keterangan = leave_type

        formatted_date = leave_date.strftime("%d-%m-%Y")

        # Urutan kolom: Tanggal | Editor | Judul | Link | Views | Keterangan
        row = [formatted_date, editor, "", "", "", keterangan]

        ws_vod   = get_or_create_worksheet("VOD",   HEADERS_VOD)
        ws_short = get_or_create_worksheet("SHORT", HEADERS_SHORT)

        try:
            ws_vod.append_row(row)
            ws_short.append_row(row)
            st.success(
                f"✅ Entri **{keterangan}** untuk **{editor}** "
                f"pada **{formatted_date}** berhasil disimpan!"
            )
        except Exception as e:
            st.error(f"❌ Gagal menyimpan entri: {e}")