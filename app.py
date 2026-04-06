"""
YT Sheet Tracker — Dibangun ulang dari nol.
Arsitektur: state-driven, modular, validasi ketat sebelum submit.
"""

import re
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# ══════════════════════════════════════════════════════════════════════
# KONFIGURASI HALAMAN (harus baris pertama Streamlit)
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="YT Sheet Tracker",
    page_icon="🎬",
    layout="wide",
)

# ══════════════════════════════════════════════════════════════════════
# KONSTANTA
# ══════════════════════════════════════════════════════════════════════
SPREADSHEET_ID = "1BrvBpYU7yr1Vcvoeqae70B1Nywsv5wGM8ZLF6hDQgGA"
SHEETS_URL     = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
MAX_LINKS      = 15
SHEET_HEADERS  = ["Tanggal", "Editor", "Judul", "Link", "Views", "Keterangan"]
LEAVE_OPTIONS  = ["Libur", "Cuti", "Izin", "Sakit", "Lainnya"]
EDITOR_LIST    = ["Erricson Bernedy S"]

# Halaman navigasi
PAGE_VIDEO = "input_video"
PAGE_LEAVE = "libur_cuti"

# ══════════════════════════════════════════════════════════════════════
# SESSION STATE — inisialisasi semua state di satu tempat
# ══════════════════════════════════════════════════════════════════════
_defaults = {
    "page":          PAGE_VIDEO,   # halaman aktif
    "clear_trigger": 0,            # ubah key textbox agar benar-benar reset
    "links_raw":     "",           # isi textbox terakhir yang di-sync
    "fetch_results": [],           # list hasil fetch: {url, vid_id, status, data/error}
    "submit_result": None,         # hasil submit terakhir: {success:[], failed:[]}
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════
# GOOGLE API — cache agar tidak reconnect tiap render
# ══════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_google_clients():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds       = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    gc          = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    yt          = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])
    return spreadsheet, yt


try:
    spreadsheet, youtube = init_google_clients()
    _clients_ok = True
except Exception as _e:
    _clients_ok = False
    _clients_err = str(_e)


# ══════════════════════════════════════════════════════════════════════
# UTILITAS MURNI (tidak menyentuh session_state)
# ══════════════════════════════════════════════════════════════════════

def extract_video_id(url: str) -> str | None:
    """
    Ekstrak video ID dari berbagai format URL YouTube.
    Kembalikan None jika bukan URL YouTube valid.
    """
    url = url.strip()
    if not url:
        return None

    # Shorts: youtube.com/shorts/<id>
    m = re.search(r'shorts/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)

    # youtu.be/<id>
    m = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)

    # youtube.com/watch?v=<id>  atau  /embed/<id>
    m = re.search(r'(?:v=|embed/)([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)

    # Parsing fallback
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]

    return None


def is_youtube_url(url: str) -> bool:
    return extract_video_id(url) is not None


def parse_publish_date(iso_str: str) -> datetime | None:
    """Parse tanggal ISO dari YouTube API."""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(iso_str, fmt)
        except ValueError:
            pass
    return None


def date_to_sheets_serial(dt: datetime) -> int:
    """
    Konversi datetime ke serial number Google Sheets (Lotus 1-2-3 epoch).
    Ini memastikan kolom Tanggal dibaca sebagai DATE oleh Sheets (=ISDATE() → TRUE).
    Epoch Sheets: 30 Desember 1899.
    """
    epoch = datetime(1899, 12, 30)
    delta = dt.replace(tzinfo=None) - epoch
    return delta.days


def extract_editor(description: str) -> str:
    """Ambil nama editor dari baris 'Editor Video: ...' di deskripsi."""
    for line in description.splitlines():
        if re.search(r'editor\s+video\s*:', line, re.IGNORECASE):
            parts = line.split(":", 1)
            if len(parts) > 1:
                name = parts[1].strip()
                if name:
                    return name
    return "Tidak Diketahui"


def build_keterangan(title: str) -> str:
    """Isi Keterangan berdasarkan judul video."""
    if "#SAKSIKATA" in title:
        return "Saksi Kata"
    return ""


def get_or_create_worksheet(name: str, headers: list):
    """Ambil worksheet; buat baru dengan header jika belum ada."""
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="USER_ENTERED")
        return ws


# ══════════════════════════════════════════════════════════════════════
# LOGIKA FETCH & SUBMIT
# ══════════════════════════════════════════════════════════════════════

def fetch_videos(urls: list[str]) -> list[dict]:
    """
    Fetch data video dari YouTube API untuk daftar URL.
    Return list of dicts:
      {url, vid_id, status: "ok"|"error", data: {...} | error: str}
    """
    # Mapping vid_id → url (deduplicate berdasarkan vid_id)
    id_to_url: dict[str, str] = {}
    invalid:   list[dict]     = []

    for url in urls:
        vid_id = extract_video_id(url)
        if vid_id:
            # Simpan URL pertama yang ditemukan untuk setiap vid_id
            if vid_id not in id_to_url:
                id_to_url[vid_id] = url
        else:
            invalid.append({"url": url, "vid_id": None, "status": "error",
                            "error": "Bukan URL YouTube yang valid"})

    results: list[dict] = list(invalid)

    if id_to_url:
        try:
            resp = youtube.videos().list(
                part="snippet,statistics",
                id=",".join(id_to_url.keys())
            ).execute()
        except Exception as e:
            # Semua gagal sekaligus
            for vid_id, url in id_to_url.items():
                results.append({"url": url, "vid_id": vid_id, "status": "error",
                                "error": f"YouTube API error: {e}"})
            return results

        returned_ids = {item["id"] for item in resp.get("items", [])}

        # Video yang tidak dikembalikan API = tidak ditemukan
        for vid_id, url in id_to_url.items():
            if vid_id not in returned_ids:
                results.append({"url": url, "vid_id": vid_id, "status": "error",
                                "error": "Video tidak ditemukan (mungkin private/dihapus)"})

        for item in resp.get("items", []):
            vid_id  = item["id"]
            url     = id_to_url[vid_id]
            snippet = item.get("snippet", {})
            stats   = item.get("statistics", {})
            results.append({
                "url":    url,
                "vid_id": vid_id,
                "status": "ok",
                "data": {
                    "title":       snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published":   snippet.get("publishedAt", ""),
                    "views":       int(stats.get("viewCount", 0)),
                },
            })

    return results


def process_and_submit(fetch_results: list[dict]) -> dict:
    """
    Proses data valid, kirim ke Google Sheets.
    Return: {success: [title, ...], failed: [{url, reason}, ...]}
    """
    ws_vod   = get_or_create_worksheet("VOD",   SHEET_HEADERS)
    ws_short = get_or_create_worksheet("SHORT", SHEET_HEADERS)

    success_list = []
    failed_list  = []

    for item in fetch_results:
        if item["status"] != "ok":
            failed_list.append({"url": item["url"], "reason": item["error"]})
            continue

        try:
            d          = item["data"]
            title      = d["title"]
            desc       = d["description"]
            pub_iso    = d["published"]
            views      = d["views"]
            url        = item["url"]

            editor      = extract_editor(desc)
            keterangan  = build_keterangan(title)

            dt = parse_publish_date(pub_iso)
            if dt is None:
                raise ValueError(f"Gagal parsing tanggal: {pub_iso!r}")

            tanggal_serial = date_to_sheets_serial(dt)

            row = [tanggal_serial, editor, title, url, views, keterangan]

            ws = ws_short if "/shorts/" in url else ws_vod
            ws.append_row(row, value_input_option="USER_ENTERED")

            success_list.append(title)

        except Exception as e:
            failed_list.append({"url": item["url"], "reason": str(e)})

    return {"success": success_list, "failed": failed_list}


# ══════════════════════════════════════════════════════════════════════
# STYLING — dark-mode friendly, minimal override
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Sembunyikan sidebar bawaan ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Hapus padding atas default Streamlit ── */
[data-testid="stAppViewContainer"] > .main > .block-container {
    padding-top: 0 !important;
}

/* ── Navbar ── */
.yt-navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #1E1E1E;
    border-bottom: 1px solid #333;
    padding: 0 24px;
    height: 52px;
    position: sticky;
    top: 0;
    z-index: 999;
    margin-bottom: 28px;
    box-shadow: 0 1px 8px rgba(0,0,0,.4);
}
.yt-navbar-brand {
    font-weight: 700;
    font-size: 15px;
    color: #f0f0f0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.yt-navbar-links { display: flex; gap: 4px; }
.yt-navbar-right { display: flex; align-items: center; gap: 8px; }

/* ── Kartu preview video ── */
.yt-card {
    background: #1E1E1E;
    border: 1px solid #333;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.yt-card-num   { font-size: 10px; font-weight: 700; letter-spacing: .06em;
                 text-transform: uppercase; color: #E8472A; font-family: monospace; }
.yt-card-title { font-weight: 600; font-size: 14px; color: #f0f0f0; margin: 4px 0; }
.yt-card-meta  { font-size: 12px; color: #888; font-family: monospace; }
.badge {
    display: inline-block; font-size: 10px; font-weight: 700;
    letter-spacing: .05em; padding: 2px 8px; border-radius: 20px; margin-top: 4px;
}
.badge-short { background: #3B1515; color: #F87171; }
.badge-vod   { background: #1B2A3B; color: #60A5FA; }
.badge-error { background: #2A1A0A; color: #FB923C; }

/* ── Warn box ── */
.warn-box {
    background: #2A1A0A;
    border: 1.5px solid #92400E;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #FCD34D;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# NAVBAR — dirender menggunakan st.button agar tidak reload
# ══════════════════════════════════════════════════════════════════════
def render_navbar():
    col_brand, col_nav, col_right = st.columns([2, 3, 2])

    with col_brand:
        st.markdown(
            '<div class="yt-navbar-brand">🎬 YT Sheet Tracker</div>',
            unsafe_allow_html=True,
        )

    with col_nav:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "📥 Input Video",
                use_container_width=True,
                type="primary" if st.session_state.page == PAGE_VIDEO else "secondary",
            ):
                st.session_state.page = PAGE_VIDEO
                st.rerun()
        with c2:
            if st.button(
                "🗓️ Libur & Cuti",
                use_container_width=True,
                type="primary" if st.session_state.page == PAGE_LEAVE else "secondary",
            ):
                st.session_state.page = PAGE_LEAVE
                st.rerun()

    with col_right:
        st.link_button("📊 Buka Google Sheets", SHEETS_URL, use_container_width=True)


render_navbar()

# Cek koneksi Google API
if not _clients_ok:
    st.error(f"❌ Gagal konek ke Google API: {_clients_err}")
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# HALAMAN 1 — INPUT VIDEO YOUTUBE
# ══════════════════════════════════════════════════════════════════════
def page_input_video():
    st.subheader("📥 Input Video YouTube")
    st.caption("Masukkan satu atau beberapa link YouTube, lalu fetch data sebelum mengirim ke Google Sheets.")

    # ── TEXTBOX INPUT ─────────────────────────────────────────────
    input_key = f"links_input_{st.session_state.clear_trigger}"
    links_raw = st.text_area(
        label="Link YouTube (satu per baris):",
        value=st.session_state.links_raw,
        placeholder=(
            "https://www.youtube.com/watch?v=...\n"
            "https://youtu.be/...\n"
            "https://www.youtube.com/shorts/..."
        ),
        height=200,
        key=input_key,
    )
    # Sinkronkan ke session_state setiap render
    st.session_state.links_raw = links_raw

    # ── PARSE URL dari textbox ─────────────────────────────────────
    raw_lines = [l.strip() for l in links_raw.splitlines() if l.strip()]
    valid_urls   = [u for u in raw_lines if is_youtube_url(u)]
    invalid_urls = [u for u in raw_lines if not is_youtube_url(u)]

    # Tampilkan ringkasan validasi URL
    if raw_lines:
        col_a, col_b = st.columns(2)
        col_a.metric("✅ URL valid", len(valid_urls))
        col_b.metric("❌ URL tidak valid", len(invalid_urls))

        if len(valid_urls) > MAX_LINKS:
            st.warning(
                f"⚠️ Maksimal {MAX_LINKS} link per submit. "
                f"Hanya {MAX_LINKS} link pertama yang akan diproses."
            )
            valid_urls = valid_urls[:MAX_LINKS]

        if invalid_urls:
            with st.expander(f"⚠️ {len(invalid_urls)} baris bukan URL YouTube valid", expanded=False):
                for u in invalid_urls:
                    st.markdown(f'<div class="warn-box">🔗 {u}</div>', unsafe_allow_html=True)

    # ── TOMBOL FETCH ──────────────────────────────────────────────
    st.markdown("")
    col_fetch, col_clear = st.columns([3, 1])

    with col_fetch:
        fetch_disabled = len(valid_urls) == 0
        do_fetch = st.button(
            "🔍 Fetch Data Video",
            use_container_width=True,
            disabled=fetch_disabled,
            help="Ambil data video dari YouTube. Wajib sebelum kirim ke Sheets.",
        )

    with col_clear:
        do_clear = st.button("🗑️ Reset", use_container_width=True)

    if do_clear:
        st.session_state.links_raw     = ""
        st.session_state.fetch_results = []
        st.session_state.submit_result = None
        st.session_state.clear_trigger += 1
        st.rerun()

    if do_fetch:
        st.session_state.submit_result = None  # reset hasil submit sebelumnya
        with st.spinner(f"Mengambil data {len(valid_urls)} video dari YouTube..."):
            st.session_state.fetch_results = fetch_videos(valid_urls)
        st.rerun()

    # ── TAMPILKAN HASIL FETCH ─────────────────────────────────────
    fetch_results = st.session_state.fetch_results
    ok_results    = [r for r in fetch_results if r["status"] == "ok"]
    err_results   = [r for r in fetch_results if r["status"] != "ok"]

    if fetch_results:
        st.markdown("---")
        st.markdown(f"**Hasil Fetch** — {len(ok_results)} berhasil, {len(err_results)} gagal")

        # Kartu preview — 3 per baris
        if ok_results:
            for row_start in range(0, len(ok_results), 3):
                cols = st.columns(3)
                for i, item in enumerate(ok_results[row_start:row_start + 3]):
                    d       = item["data"]
                    url     = item["url"]
                    is_short = "/shorts/" in url
                    badge   = (
                        '<span class="badge badge-short">SHORT</span>'
                        if is_short else
                        '<span class="badge badge-vod">VOD</span>'
                    )
                    dt = parse_publish_date(d["published"])
                    date_str = dt.strftime("%d-%m-%Y") if dt else d["published"]
                    num = row_start + i + 1

                    with cols[i]:
                        st.markdown(f"""
                        <div class="yt-card">
                            <div class="yt-card-num">#{num}</div>
                            <div class="yt-card-title">{d['title']}</div>
                            <div class="yt-card-meta">
                                📅 {date_str} &nbsp;|&nbsp; 👁 {d['views']:,}
                            </div>
                            <div class="yt-card-meta">
                                ✏️ {extract_editor(d['description'])}
                            </div>
                            {badge}
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"[🔗 Buka Video]({url})")

        # Error fetch
        if err_results:
            with st.expander(f"❌ {len(err_results)} video gagal di-fetch", expanded=True):
                for item in err_results:
                    st.markdown(
                        f'<div class="warn-box">🔗 <code>{item["url"]}</code><br>'
                        f'Alasan: {item["error"]}</div>',
                        unsafe_allow_html=True,
                    )

    # ── TOMBOL SUBMIT ─────────────────────────────────────────────
    if fetch_results:
        st.markdown("")
        submit_disabled = len(ok_results) == 0
        do_submit = st.button(
            f"▶️ Kirim {len(ok_results)} Video ke Google Sheets",
            use_container_width=True,
            type="primary",
            disabled=submit_disabled,
            help="Hanya data yang berhasil di-fetch yang akan dikirim.",
        )

        if do_submit:
            with st.spinner("Mengirim data ke Google Sheets..."):
                result = process_and_submit(fetch_results)
            st.session_state.submit_result = result

            # Tentukan reset atau tidak
            all_failed = len(result["success"]) == 0
            if not all_failed:
                # Ada yang berhasil → kosongkan form
                remaining_urls = [f["url"] for f in result["failed"]]
                if remaining_urls:
                    # Sisakan yang gagal
                    st.session_state.links_raw     = "\n".join(remaining_urls)
                    st.session_state.clear_trigger += 1
                else:
                    # Semua sukses → reset penuh
                    st.session_state.links_raw     = ""
                    st.session_state.clear_trigger += 1
                st.session_state.fetch_results = []
            # all_failed → jangan reset, biarkan user coba lagi

            st.rerun()

    # ── TAMPILKAN HASIL SUBMIT ─────────────────────────────────────
    submit_result = st.session_state.submit_result
    if submit_result:
        if submit_result["success"]:
            st.success(
                f"🎉 **{len(submit_result['success'])} video** berhasil dikirim ke Google Sheets!"
            )
            with st.expander("Lihat daftar video yang berhasil", expanded=False):
                for title in submit_result["success"]:
                    st.markdown(f"- {title}")

        if submit_result["failed"]:
            st.error(
                f"❌ **{len(submit_result['failed'])} video** gagal dikirim:"
            )
            for f in submit_result["failed"]:
                st.markdown(
                    f'<div class="warn-box">🔗 <code>{f["url"]}</code><br>'
                    f'Alasan: {f["reason"]}</div>',
                    unsafe_allow_html=True,
                )

        if not submit_result["success"] and not submit_result["failed"]:
            st.warning("⚠️ Tidak ada data yang diproses.")


# ══════════════════════════════════════════════════════════════════════
# HALAMAN 2 — LIBUR & CUTI
# ══════════════════════════════════════════════════════════════════════
def page_libur_cuti():
    st.subheader("🗓️ Entri Hari Libur & Cuti")
    st.caption("Catat ketidakhadiran editor ke Google Sheets (sheet VOD & SHORT).")

    col_form, _ = st.columns([2, 1])

    with col_form:
        leave_date = st.date_input("📅 Tanggal")
        leave_type = st.selectbox("📋 Jenis Kegiatan", LEAVE_OPTIONS)

        custom_activity = ""
        if leave_type == "Lainnya":
            custom_activity = st.text_input(
                "✏️ Isi Kegiatan *",
                placeholder="Contoh: Rapat, Perjalanan Dinas, dll.",
            )

        editor = st.selectbox("👤 Editor", EDITOR_LIST)

        st.markdown("")
        do_save = st.button("💾 Simpan Entri", type="primary", use_container_width=True)

        st.info(
            "📌 **Info:** Entri akan dicatat ke sheet **VOD** dan **SHORT** sekaligus, "
            "pada kolom *Keterangan*."
        )

    # ── VALIDASI & SIMPAN ─────────────────────────────────────────
    if do_save:
        if leave_type == "Lainnya":
            if not custom_activity.strip():
                st.error("❌ Kolom 'Isi Kegiatan' wajib diisi saat memilih 'Lainnya'.")
                st.stop()
            keterangan = custom_activity.strip()
        else:
            keterangan = leave_type

        # Gunakan serial date agar Sheets membaca sebagai DATE
        dt_leave       = datetime(leave_date.year, leave_date.month, leave_date.day)
        tanggal_serial = date_to_sheets_serial(dt_leave)

        # Urutan kolom: Tanggal | Editor | Judul | Link | Views | Keterangan
        row = [tanggal_serial, editor, "", "", "", keterangan]

        try:
            ws_vod   = get_or_create_worksheet("VOD",   SHEET_HEADERS)
            ws_short = get_or_create_worksheet("SHORT", SHEET_HEADERS)

            ws_vod.append_row(row,   value_input_option="USER_ENTERED")
            ws_short.append_row(row, value_input_option="USER_ENTERED")

            st.success(
                f"✅ Entri **{keterangan}** untuk **{editor}** "
                f"pada **{leave_date.strftime('%d-%m-%Y')}** berhasil disimpan!"
            )
        except Exception as e:
            st.error(f"❌ Gagal menyimpan entri: {e}")


# ══════════════════════════════════════════════════════════════════════
# ROUTER — tampilkan halaman sesuai state
# ══════════════════════════════════════════════════════════════════════
if st.session_state.page == PAGE_VIDEO:
    page_input_video()
else:
    page_libur_cuti()