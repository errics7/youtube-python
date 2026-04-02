import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────────
# KONFIGURASI HALAMAN & STYLING
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="YT Sheet Tracker",
    page_icon="🎬",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Root variables ── */
:root {
    --bg:        #F5F4F0;
    --surface:   #FFFFFF;
    --surface2:  #EEECEA;
    --border:    #D8D5CF;
    --accent:    #E8472A;
    --accent2:   #2A6AE8;
    --text:      #1A1916;
    --muted:     #7A776F;
    --success:   #1E8C5A;
    --warning:   #D97706;
    --radius:    12px;
    --shadow:    0 2px 12px rgba(0,0,0,0.08);
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text);
}

.stApp { background: var(--bg); }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    transition: all .18s ease !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,.12) !important; }

/* ── Text areas & inputs ── */
.stTextArea textarea, .stTextInput input {
    border-radius: 8px !important;
    border: 1.5px solid var(--border) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
    background: var(--surface) !important;
    transition: border-color .15s;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent2) !important;
    box-shadow: 0 0 0 3px rgba(42,106,232,.12) !important;
}

/* ── Select boxes ── */
.stSelectbox select, [data-baseweb="select"] {
    border-radius: 8px !important;
}

/* ── Dividers ── */
hr { border-color: var(--border) !important; }

/* ── Metric ── */
[data-testid="stMetricValue"] { font-family: 'DM Mono', monospace !important; }

/* ── Custom card ── */
.yt-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 8px;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    gap: 4px;
    transition: box-shadow .18s;
}
.yt-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,.12); }
.yt-card-num {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--accent);
    font-family: 'DM Mono', monospace;
}
.yt-card-title { font-weight: 600; font-size: 14px; color: var(--text); }
.yt-card-meta { font-size: 12px; color: var(--muted); font-family: 'DM Mono', monospace; }
.yt-card-type {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .05em;
    padding: 2px 8px;
    border-radius: 20px;
    margin-top: 4px;
}
.badge-short { background: #FEE2E2; color: #B91C1C; }
.badge-vod   { background: #DBEAFE; color: #1D4ED8; }

.warn-box {
    background: #FEF9EC;
    border: 1.5px solid #F59E0B;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #92400E;
    margin-bottom: 8px;
}

.page-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
}
.page-header-icon {
    font-size: 36px;
    line-height: 1;
}
.page-header-title {
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    margin: 0;
}
.page-header-sub {
    font-size: 13px;
    color: var(--muted);
    margin: 0;
}

.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KONSTANTA
# ─────────────────────────────────────────────
SPREADSHEET_ID = "1BrvBpYU7yr1Vcvoeqae70B1Nywsv5wGM8ZLF6hDQgGA"
SHEETS_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
MAX_LINKS = 15


# ─────────────────────────────────────────────
# AUTENTIKASI & INISIALISASI GOOGLE API
# ─────────────────────────────────────────────
@st.cache_resource
def init_google_clients():
    """Inisialisasi Google Sheets & YouTube API (di-cache agar tidak login ulang tiap interaksi)."""
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    youtube = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])
    return spreadsheet, youtube

spreadsheet, youtube = init_google_clients()


# ─────────────────────────────────────────────
# FUNGSI UTILITAS
# ─────────────────────────────────────────────
def get_video_id(url: str):
    """Ekstrak video ID dari berbagai format URL YouTube."""
    # Shorts
    shorts_match = re.search(r'shorts/([a-zA-Z0-9_-]{11})', url)
    if shorts_match:
        return shorts_match.group(1)

    # Standard watch URL
    yt_match = re.search(r'(?:v=|youtu\.be/|embed/|watch\?v=)([^&"?\s]{11})', url)
    if yt_match:
        return yt_match.group(1)

    # Fallback parse
    parsed_url = urlparse(url)
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]

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
    return "Tidak tercantum"


def get_or_create_worksheet(name: str, headers: list):
    """Ambil worksheet; buat baru dengan header jika belum ada."""
    try:
        return spreadsheet.worksheet(name)
    except Exception:
        ws = spreadsheet.add_worksheet(name, 1000, 10)
        ws.append_row(headers)
        return ws


# ─────────────────────────────────────────────
# SIDEBAR – NAVIGASI
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 YT Sheet Tracker")
    st.markdown("---")
    page = st.radio(
        "Menu",
        ["📥  Input Video YouTube", "🗓️  Libur & Cuti"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.link_button("📊 Buka Google Sheets", SHEETS_URL, use_container_width=True)
    st.markdown(f"<div style='font-size:11px;color:var(--muted);margin-top:8px;text-align:center'>Max {MAX_LINKS} link per sesi</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# HALAMAN 1 – INPUT VIDEO YOUTUBE
# ═══════════════════════════════════════════════════════════════════
if "📥" in page:

    st.markdown("""
    <div class="page-header">
        <div class="page-header-icon">📥</div>
        <div>
            <div class="page-header-title">Input Video YouTube</div>
            <div class="page-header-sub">Rekam data video ke Google Sheets secara otomatis</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SESSION STATE ──────────────────────────────────────────────
    # Menyimpan status lintas interaksi agar link bisa dikosongkan setelah berhasil kirim
    if "links_text" not in st.session_state:
        st.session_state.links_text = ""
    if "preview_data" not in st.session_state:
        st.session_state.preview_data = []

    # ── INPUT LINKS ────────────────────────────────────────────────
    st.markdown('<div class="section-label">Masukkan Link YouTube</div>', unsafe_allow_html=True)

    links_text = st.text_area(
        label="links_input",
        value=st.session_state.links_text,
        placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...\nhttps://www.youtube.com/shorts/...",
        height=220,
        label_visibility="collapsed",
        key="links_input_area"
    )

    # Simpan ke session state
    st.session_state.links_text = links_text

    # ── PARSE & VALIDASI LINKS ─────────────────────────────────────
    raw_lines = [l.strip() for l in links_text.split("\n") if l.strip()]

    invalid_lines = []
    valid_links   = []
    for i, line in enumerate(raw_lines, 1):
        if get_video_id(line):
            valid_links.append((i, line))
        else:
            invalid_lines.append((i, line))

    # Tampilkan nomor baris secara ringkas
    if raw_lines:
        col_cnt, col_warn = st.columns([3, 2])
        with col_cnt:
            st.markdown(
                f"<div style='font-size:13px;color:var(--muted)'>"
                f"✅ <b>{len(valid_links)}</b> link valid &nbsp;|&nbsp; "
                f"{'⚠️ <b>' + str(len(invalid_lines)) + '</b> baris bukan link YouTube' if invalid_lines else '🎉 Semua baris valid'}"
                f"</div>",
                unsafe_allow_html=True
            )

    # Peringatan baris tidak valid
    if invalid_lines:
        warn_text = ", ".join([f"Baris {i}" for i, _ in invalid_lines])
        st.markdown(
            f'<div class="warn-box">⚠️ Baris berikut bukan link YouTube yang valid dan akan dilewati: <b>{warn_text}</b></div>',
            unsafe_allow_html=True
        )

    if len(valid_links) > MAX_LINKS:
        st.error(f"❌ Maksimal {MAX_LINKS} link YouTube per pengiriman.")
        valid_links = valid_links[:MAX_LINKS]

    # ── TOMBOL PREVIEW + KIRIM (sticky atas) ──────────────────────
    col_prev, col_send, col_clear = st.columns([2, 2, 1])

    with col_prev:
        btn_preview = st.button("🔍 Preview Video", use_container_width=True, type="secondary")
    with col_send:
        btn_send = st.button("▶️ Kirim ke Google Sheets", use_container_width=True, type="primary")
    with col_clear:
        btn_clear = st.button("🗑️ Hapus", use_container_width=True)

    if btn_clear:
        st.session_state.links_text = ""
        st.session_state.preview_data = []
        st.rerun()

    # ── FETCH PREVIEW DATA ─────────────────────────────────────────
    video_ids    = [get_video_id(url) for _, url in valid_links]
    original_map = {get_video_id(url): url for _, url in valid_links}

    if btn_preview and video_ids:
        with st.spinner("Mengambil data video..."):
            resp = youtube.videos().list(part="snippet", id=",".join(video_ids)).execute()
            st.session_state.preview_data = resp.get("items", [])

    # ── TAMPILKAN PREVIEW ──────────────────────────────────────────
    if st.session_state.preview_data:
        st.markdown("---")
        st.markdown('<div class="section-label">Preview Video</div>', unsafe_allow_html=True)

        items = st.session_state.preview_data
        # Tampilkan 3 kartu per baris
        for row_start in range(0, len(items), 3):
            cols = st.columns(3)
            for col_idx, item in enumerate(items[row_start:row_start+3]):
                vid_id    = item["id"]
                title     = item["snippet"]["title"]
                published = item["snippet"]["publishedAt"]
                url       = original_map.get(vid_id, "")
                is_short  = "/shorts/" in url
                badge     = '<span class="yt-card-type badge-short">SHORT</span>' if is_short else '<span class="yt-card-type badge-vod">VOD</span>'
                num       = row_start + col_idx + 1

                with cols[col_idx]:
                    st.markdown(f"""
                    <div class="yt-card">
                        <div class="yt-card-num">#{num}</div>
                        <div class="yt-card-title">{title}</div>
                        <div class="yt-card-meta">📅 {format_date(published)}</div>
                        {badge}
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"[🔗 Buka Video]({url})", unsafe_allow_html=False)

    # ── KIRIM KE GOOGLE SHEETS ─────────────────────────────────────
    if btn_send:
        if not video_ids:
            st.error("❌ Tidak ada link YouTube yang valid untuk dikirim.")
        else:
            HEADERS = ["Judul", "Link", "Editor", "Upload", "Views", "Keterangan"]
            ws_short = get_or_create_worksheet("SHORT", HEADERS)
            ws_vod   = get_or_create_worksheet("VOD",   HEADERS)

            with st.spinner("Mengirim data ke Google Sheets..."):
                resp = youtube.videos().list(
                    part="snippet,statistics",
                    id=",".join(video_ids)
                ).execute()

            success_titles = []
            failed_ids     = []

            for item in resp.get("items", []):
                try:
                    vid_id  = item["id"]
                    title   = item["snippet"]["title"]
                    desc    = item["snippet"].get("description", "")
                    views   = item.get("statistics", {}).get("viewCount", "0")
                    pub     = item["snippet"]["publishedAt"]
                    url     = original_map.get(vid_id, "")
                    editor  = extract_editor(desc)
                    row     = [title, url, editor, format_date(pub), views, ""]

                    if "/shorts/" in url:
                        ws_short.append_row(row)
                    else:
                        ws_vod.append_row(row)

                    success_titles.append(title)
                except Exception as e:
                    failed_ids.append((vid_id, str(e)))

            if success_titles:
                st.success(f"🎉 Berhasil mengirim **{len(success_titles)}** video ke Google Sheets!")

            if failed_ids:
                for vid, err in failed_ids:
                    st.warning(f"⚠️ Gagal mengirim `{vid}`: {err}")

                # Sisakan hanya link yang gagal
                failed_set  = {v for v, _ in failed_ids}
                remaining   = "\n".join(
                    url for vid_id, url in original_map.items() if vid_id in failed_set
                )
                st.session_state.links_text    = remaining
                st.session_state.preview_data  = []
            else:
                # Semua berhasil – kosongkan input
                st.session_state.links_text   = ""
                st.session_state.preview_data = []

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

    col_form, col_info = st.columns([2, 1])

    with col_form:
        # ── FORM INPUT ─────────────────────────────────────────────
        leave_date = st.date_input("📅 Tanggal")

        # Opsi jenis kegiatan (Lainnya di urutan terakhir)
        LEAVE_OPTIONS = ["Libur", "Cuti", "Izin", "Sakit", "Lainnya"]
        leave_type = st.selectbox("📋 Jenis Kegiatan", LEAVE_OPTIONS)

        # Jika memilih "Lainnya" tampilkan text input
        custom_activity = ""
        if leave_type == "Lainnya":
            custom_activity = st.text_input(
                "✏️ Isi Kegiatan",
                placeholder="Contoh: Rapat, Perjalanan Dinas, dll."
            )
            if not custom_activity.strip():
                st.caption("⚠️ Harap isi keterangan kegiatan.")

        editor = st.selectbox("👤 Editor", ["Erricson Bernedy S"])

        st.markdown("")  # spacer
        btn_leave = st.button("💾 Simpan Entri", type="primary", use_container_width=True)

    with col_info:
        st.markdown("""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-top:36px">
            <div style="font-weight:700;font-size:14px;margin-bottom:8px">📌 Info</div>
            <div style="font-size:13px;color:var(--muted);line-height:1.7">
                Entri akan dicatat ke sheet <b>VOD</b> dan <b>SHORT</b> sekaligus, pada kolom <i>Keterangan</i>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── SIMPAN ─────────────────────────────────────────────────────
    if btn_leave:
        # Tentukan nilai keterangan
        if leave_type == "Lainnya":
            if not custom_activity.strip():
                st.error("❌ Kolom 'Isi Kegiatan' tidak boleh kosong saat memilih Lainnya.")
                st.stop()
            keterangan = custom_activity.strip()
        else:
            keterangan = leave_type

        formatted_date = leave_date.strftime("%d-%m-%Y")
        row = ["", "", editor, formatted_date, "", keterangan]

        HEADERS = ["Judul", "Link", "Editor", "Upload", "Views", "Keterangan"]
        ws_vod   = get_or_create_worksheet("VOD",   HEADERS)
        ws_short = get_or_create_worksheet("SHORT",  HEADERS)

        try:
            ws_vod.append_row(row)
            ws_short.append_row(row)
            st.success(f"✅ Entri **{keterangan}** untuk **{editor}** pada **{formatted_date}** berhasil disimpan!")
        except Exception as e:
            st.error(f"❌ Gagal menyimpan entri: {e}")