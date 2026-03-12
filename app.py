import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import re
from urllib.parse import urlparse, parse_qs

SPREADSHEET_ID = "1BrvBpYU7yr1Vcvoeqae70B1Nywsv5wGM8ZLF6hDQgGA"
YOUTUBE_API_KEY = "AIzaSyD4CJ5MRW6Kp6B0IwvrcPuci6Wi9NmCzXQ"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "youtube-data-490005-098b4548b42b.json",
    scopes=scope
)

gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

st.title("YouTube Link & Leave Entry Automation")

st.subheader("Input Link YouTube")

links_text = st.text_area(
    "Masukkan link YouTube (maks 15 link, satu per baris)",
    height=200
)

links = [l.strip() for l in links_text.split("\n") if l.strip()]

if len(links) > 15:
    st.error("❌ Maksimal 15 link")
else:
    st.write(f"Jumlah link: {len(links)}")

def get_video_id(url):
    yt_match = re.search(r'(?:v=|youtu\.be/|embed/|watch\?v=)([^&"?\s]{11})', url)
    if yt_match:
        return yt_match.group(1)

    shorts_match = re.search(r'shorts/([a-zA-Z0-9_-]{11})', url)
    if shorts_match:
        return shorts_match.group(1)

    parsed_url = urlparse(url)
    if parsed_url.hostname in ('www.youtube.com','youtube.com','m.youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]

    return None

video_ids = []
original_urls = {}

for url in links:
    vid = get_video_id(url)
    if vid:
        video_ids.append(vid)
        original_urls[vid] = url

if video_ids:

    st.subheader("Preview Video")

    request = youtube.videos().list(
        part="snippet",
        id=",".join(video_ids)
    )

    response = request.execute()

    for item in response.get("items", []):

        title = item["snippet"]["title"]
        published = item["snippet"]["publishedAt"]
        video_id = item["id"]

        try:
            date_obj = datetime.strptime(published,"%Y-%m-%dT%H:%M:%SZ")
            formatted_date = date_obj.strftime("%d-%m-%Y")
        except:
            formatted_date = published

        url = original_urls.get(video_id)

        st.markdown(f"**{title}**")
        st.write(f"Upload: {formatted_date}")
        st.markdown(f"[Open Video]({url})")
        st.divider()

if st.button("▶️ Kirim ke Google Sheet"):

    if not video_ids:
        st.error("Tidak ada video valid")
    else:

        try:
            ws_short = spreadsheet.worksheet("SHORT")
        except:
            ws_short = spreadsheet.add_worksheet("SHORT",1000,10)
            ws_short.append_row(["Judul","Link","Editor","Upload","Views","Keterangan"])

        try:
            ws_vod = spreadsheet.worksheet("VOD")
        except:
            ws_vod = spreadsheet.add_worksheet("VOD",1000,10)
            ws_vod.append_row(["Judul","Link","Editor","Upload","Views","Keterangan"])

        request = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids)
        )

        response = request.execute()

        success = 0

        for item in response.get("items", []):

            title = item["snippet"]["title"]
            desc = item["snippet"].get("description","")
            views = item.get("statistics",{}).get("viewCount","0")
            published = item["snippet"]["publishedAt"]
            video_id = item["id"]

            try:
                date_obj = datetime.strptime(published,"%Y-%m-%dT%H:%M:%SZ")
                formatted_date = date_obj.strftime("%d-%m-%Y")
            except:
                formatted_date = published

            url = original_urls.get(video_id)

            editor = "Tidak tercantum"

            for line in desc.split("\n"):
                if "editor video" in line.lower():
                    parts = line.split(":",1)
                    if len(parts)>1:
                        editor = parts[1].strip()
                    break

            sheet_name = "SHORT" if "/shorts/" in url else "VOD"

            row = [title,url,editor,formatted_date,views,""]

            if sheet_name == "SHORT":
                ws_short.append_row(row)
            else:
                ws_vod.append_row(row)

            success += 1

        st.success(f"🎉 Berhasil mengirim {success} video ke Google Sheets")

st.subheader("Entri Hari Libur / Cuti")

leave_date = st.date_input("Tanggal")
leave_type = st.selectbox("Jenis",["Libur","Cuti","Kegiatan Lain","Izin","Sakit"])
editor = st.selectbox("Editor",["Erricson Bernedy S"])

if st.button("Kirim Entri Cuti"):

    formatted_date = leave_date.strftime("%d-%m-%Y")
    row = ["","",editor,formatted_date,"",leave_type]

    try:
        ws = spreadsheet.worksheet("VOD")
    except:
        ws = spreadsheet.add_worksheet("VOD",1000,10)

    ws.append_row(row)

    try:
        ws2 = spreadsheet.worksheet("SHORT")
    except:
        ws2 = spreadsheet.add_worksheet("SHORT",1000,10)

    ws2.append_row(row)

    st.success("Entri cuti berhasil disimpan")
