import gspread
from google.colab import auth
from google.auth import default
from ipywidgets import DatePicker
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
from datetime import datetime

# Imports for YouTube Data API
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import re
from urllib.parse import urlparse, parse_qs

# ===============================
# AUTH GOOGLE SHEET
# ===============================
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)
SPREADSHEET_ID = "1BrvBpYU7yr1Vcvoeqae70B1Nywsv5wGM8ZLF6hDQgGA"
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

# ===============================
# YOUTUBE DATA API INITIALIZATION
# ===============================
# IMPORTANT: Replace 'YOUR_API_KEY' with your actual YouTube Data API v3 key
YOUTUBE_API_KEY = 'AIzaSyDXgnpJDu88APxY9LYRJl7faR9QwxlSE8U'

# Initialize the YouTube Data API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
print("YouTube Data API client initialized.")

# ===============================
# UI for Link Submission
# ===============================
input_links = widgets.Textarea(
    placeholder="15 Link Perbaris Short/VOD",
    layout=widgets.Layout(width="600px", height="150px", margin='0 0 10px 0')
)

process_btn = widgets.Button(
    description="▶️ Kirim ke Sheet", # Initial text
    button_style="success"
)

reset_btn = widgets.Button(
    description="🔁 Kirim Link Lagi",
    button_style="warning"
)

output = widgets.Output()

# New widget to display link count and warnings
link_count_display = widgets.HTML(layout=widgets.Layout(margin='0 0 10px 0'))

# Define a new ipywidgets.Output() widget named live_preview_output for live video descriptions
live_preview_output = widgets.Output(
    layout=widgets.Layout(
        border='1px solid #c7d2e4',
        padding='10px',
        margin='10px 0',
        background_color='#f0f4fa',
        border_radius='5px'
    )
)

# Function to update link count display
def update_link_count_display(change):
    links = [l.strip() for l in input_links.value.split("\n") if l.strip()]
    count = len(links)
    if count > 15:
        link_count_display.value = f'<span style="color: red;">❌ Batas maksimal 15 link (Saat ini: {count})</span>'
    elif count == 0:
        link_count_display.value = '<span>Jumlah link: 0</span>'
    else:
        link_count_display.value = f'<span>Jumlah link: {count}</span>'

# Observe changes in input_links to update the count display
input_links.observe(update_link_count_display, names='value')

# Initialize the display
update_link_count_display(None)

# Temporary test for live_preview_output rendering
with live_preview_output:
    display(HTML("<i>Testing live_preview_output...</i>"))


# Global variable (still useful for storing processed data temporarily within the function call)
processed_links_data = [] # This list will be populated and then immediately sent

# ===============================
# UI Entri Cuti/Kegiatan
# ===============================
leave_date_picker = widgets.DatePicker(
    description='Pilih Tanggal',
    disabled=False,
    value=datetime.now().date()
)
# tempat mengganti dropdown oprtion libur
leave_type_dropdown = widgets.Dropdown(
    options=['Libur', 'Cuti', 'Kegiatan Lain', 'Izin', 'Sakit'],
    value='Libur',
    description='Jenis:',
    disabled=False,
)

# New dropdown for Editor
leave_editor_dropdown = widgets.Dropdown(
    options=['Erricson Bernedy S'], # Pre-filled with the specified name
    value='Erricson Bernedy S',
    description='Editor:',
    disabled=False,
)

leave_submit_btn = widgets.Button(
    description='Kirim Entri',
    button_style='info'
)

leave_reset_btn = widgets.Button(
    description='Reset',
    button_style='warning'
)

leave_output = widgets.Output() # Separate output for leave entries

# Helper function to extract video ID from YouTube URL
def get_video_id(url):
    yt_match = re.search(r'(?:v=|youtu\.be/|embed/|watch\?v=)([^&"?\s]{11})', url)
    if yt_match:
        return yt_match.group(1)
    shorts_match = re.search(r'shorts/([a-zA-Z0-9_-]{11})', url)
    if shorts_match:
        return shorts_match.group(1)
    parsed_url = urlparse(url)
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    return None

# Function to update live preview
def update_live_preview(change):
    with live_preview_output:
        clear_output(wait=True)

        links_text = change['new']
        links = [l.strip() for l in links_text.split("\n") if l.strip()]

        if not links:
            display(HTML("<i>Masukkan link YouTube untuk melihat pratinjau.</i>"))
            return

        html_output = "<b>Pratinjau Link:</b><br>"

        video_ids = []
        original_urls = {}

        for url in links:
            video_id = get_video_id(url)
            if video_id:
                video_ids.append(video_id)
                original_urls[video_id] = url

        if not video_ids:
            display(HTML("<i>Tidak ada link YouTube yang valid ditemukan.</i>"))
            return

        try:
            request = youtube.videos().list(
                part="snippet",
                id=",".join(video_ids)
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]
                title = item["snippet"]["title"]
                published_at = item["snippet"]["publishedAt"]
                url = original_urls.get(video_id)

                try:
                    date_obj = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')
                    formatted_date = date_obj.strftime('%d-%m-%Y')
                except:
                    formatted_date = published_at

                html_output += f"- <a href='{url}' target='_blank'>{title}</a> (Upload: {formatted_date})<br>"

        except Exception as e:
            html_output += f"<span style='color:red;'>❌ Error: {e}</span>"

        display(HTML(html_output))

# Observe changes in input_links to trigger live preview
input_links.observe(update_live_preview, names='value')

# ===============================
# MODIFIED FUNGSI process_links (Direct Send ke Sheet)
# ===============================
def process_links(b):
    with output:
        clear_output()
        process_btn.description = "Memproses & Mengirim..." # Indicate ongoing process

        links = [l.strip() for l in input_links.value.split("\n") if l.strip()]

        if not links:
            print("❌ Link kosong")
            process_btn.description = "▶️ Kirim ke Sheet"
            return
        if len(links) > 15:
            print("❌ Maksimal 15 link")
            process_btn.description = "▶️ Kirim ke Sheet"
            return

        print(f"ℹ️ Memproses {len(links)} link...")

        global processed_links_data
        processed_links_data = []
        failed_links = []

        video_ids = []
        original_urls = {}
        for url in links:
            video_id = get_video_id(url)
            if video_id:
                video_ids.append(video_id)
                original_urls[video_id] = url
            else:
                failed_links.append({"url": url, "error": "Gagal mendapatkan ID video dari URL."})

        if not video_ids:
            print("❌ Tidak ada ID video yang valid ditemukan.")
            process_btn.description = "▶️ Kirim ke Sheet"
            return

        quota_exceeded = False
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
            if quota_exceeded:
                print("🛑 Menghentikan pemrosesan karena kuota API terlampaui atau kunci API tidak valid.")
                break

            current_batch_ids = video_ids[i:i+batch_size]
            try:
                request = youtube.videos().list(
                    part="snippet,statistics",
                    id=",".join(current_batch_ids)
                )
                response = request.execute()

                for item in response.get("items", []):
                    video_id = item["id"]
                    url = original_urls.get(video_id, f"https://www.youtube.com/watch?v={video_id}")

                    snippet = item.get("snippet", {})
                    statistics = item.get("statistics", {})

                    title = snippet.get("title", "N/A")
                    desc = snippet.get("description", "")
                    views = statistics.get("viewCount", "0")
                    raw_upload_date = snippet.get("publishedAt")

                    formatted_upload_date = None
                    if raw_upload_date:
                        try:
                            date_obj = datetime.strptime(raw_upload_date, '%Y-%m-%dT%H:%M:%SZ')
                            formatted_date = date_obj.strftime('%d-%m-%Y')
                        except ValueError:
                            formatted_date = raw_upload_date

                    editor = "Tidak tercantum"
                    for line in desc.split("\n"):
                        if "editor video" in line.lower():
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                editor = parts[1].strip()
                            break

                    sheet_name = "SHORT" if "/shorts/" in url else "VOD"

                    keterangan = ""
                    if sheet_name == "VOD":
                        if "#SAKSIKATA" in title:
                            keterangan = "Video SAKSIKATA"

                    processed_links_data.append({
                        'title': title,
                        'url': url,
                        'editor': editor,
                        'upload_date': formatted_date,
                        'views': views,
                        'keterangan': keterangan,
                        'sheet_name': sheet_name
                    })

                processed_ids_in_batch = {item['id'] for item in response.get('items', [])}
                for id_in_batch in current_batch_ids:
                    if id_in_batch not in processed_ids_in_batch:
                        failed_links.append({"url": original_urls.get(id_in_batch, f"https://www.youtube.com/watch?v={id_in_batch}"), "error": "Video tidak ditemukan atau tidak dapat diakses melalui API."})

            except HttpError as err:
                error_content = json.loads(err.content)
                error_message = error_content.get('error', {}).get('message', 'Unknown error.')
                error_code = error_content.get('error', {}).get('code', 0)

                if error_code == 403 and ('quotaExceeded' in error_message or 'dailyLimitExceeded' in error_message):
                    print(f"❌ ERROR: Kuota harian YouTube Data API terlampaui. ({error_message})")
                    quota_exceeded = True
                    for id_in_batch in current_batch_ids:
                        failed_links.append({"url": original_urls.get(id_in_batch, f"https://www.youtube.com/watch?v={id_in_batch}"), "error": "API Error: Kuota harian terlampaui."})
                elif error_code == 403 and ('developerKeyInvalid' in error_message or 'API key not valid' in error_message):
                    print(f"❌ ERROR: Kunci API YouTube tidak valid. Mohon periksa YOUTUBE_API_KEY Anda. ({error_message})")
                    quota_exceeded = True
                    for id_in_batch in current_batch_ids:
                        failed_links.append({"url": original_urls.get(id_in_batch, f"https://www.youtube.com/watch?v={id_in_batch}"), "error": "API Error: Kunci API tidak valid."})
                else:
                    print(f"❌ ERROR API YouTube: Status {err.resp.status}, Pesan: {error_message}")
                    for id_in_batch in current_batch_ids:
                        failed_links.append({"url": original_urls.get(id_in_batch, f"https://www.youtube.com/watch?v={id_in_batch}"), "error": f"API Error: {error_message} (Code: {error_code})"})

            except Exception as e:
                print(f"❌ ERROR tidak terduga saat memanggil API: {e}")
                for id_in_batch in current_batch_ids:
                    failed_links.append({"url": original_urls.get(id_in_batch, f"https://www.youtube.com/watch?v={id_in_batch}"), "error": f"Error tidak terduga: {e}"})

        # --- Direct submission to Google Sheet ---
        if processed_links_data:
            print(f"\nℹ️ Mengirim {len(processed_links_data)} link ke Google Sheets...")
            successful_submissions = 0
            for link_data in processed_links_data:
                sheet_name = link_data['sheet_name']
                row_data = [
                    link_data['title'],
                    link_data['url'],
                    link_data['editor'],
                    link_data['upload_date'],
                    link_data['views'],
                    link_data['keterangan']
                ]

                ws = None
                try:
                    ws = spreadsheet.worksheet(sheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    print(f"➕ Worksheet '{sheet_name}' tidak ditemukan, membuat yang baru.")
                    ws = spreadsheet.add_worksheet(sheet_name, 1000, 10)
                    ws.append_row(["Judul","Link","Editor","Upload","Views","Keterangan"]) # Add header if new sheet
                except Exception as e:
                    print(f"❌ Gagal mengakses/membuat worksheet {sheet_name} untuk link '{link_data['title']}': {e}")
                    ws = None

                if ws is not None:
                    try:
                        ws.append_row(row_data)
                        print(f"✅ Berhasil mengirim '{link_data['title']}' ke sheet '{sheet_name}'.")
                        successful_submissions += 1
                    except Exception as e:
                        print(f"❌ Gagal mengirim link '{link_data['title']}' ke sheet '{sheet_name}': {e}")
            print(f"\n🎉 Selesai! Berhasil mengirim {successful_submissions} link ke Google Sheets.")
        else:
            print("\nℹ️ Tidak ada link yang berhasil diproses untuk dikirim.")

        if failed_links:
            print("❌ Beberapa link gagal diproses dan tidak dikirim:")
            for f_link in failed_links:
                print(f"  - {f_link['url']} (Error: {f_link['error']})")

        print("\n🎉 Proses Selesai.")

        # Reset UI to initial state after processing and sending
        input_links.value = "" # Clear input field
        output.clear_output() # Clear the output area
        process_btn.description = "▶️ Kirim ke Sheet" # Reset button text

        # Ensure the preview area is also cleared after submission
        with live_preview_output:
            clear_output()
            display(HTML("<i>Masukkan link YouTube untuk melihat pratinjau.</i>"))

        # Ensure input stage elements are visible
        input_links.layout.display = 'block'
        process_btn.layout.display = 'block'
        reset_btn.layout.display = 'block'
        link_count_display.layout.display = 'block'

def reset_form(b):
    input_links.value = ""
    output.clear_output()
    with live_preview_output:
        clear_output()
        display(HTML("<i>Masukkan link YouTube untuk melihat pratinjau.</i>"))

# ===============================
# Definisikan Fungsi submit_leave_entry
# ===============================
def submit_leave_entry(b):
    with leave_output:
        clear_output()
        selected_date = leave_date_picker.value
        selected_type = leave_type_dropdown.value
        selected_editor = leave_editor_dropdown.value # Get selected editor

        print(f"DEBUG: Tanggal terpilih (DatePicker value): {selected_date}")

        if not selected_date:
            print("❌ Tanggal harus dipilih.")
            return
        if not selected_type:
            print("❌ Jenis kegiatan harus dipilih.")
            return
        if not selected_editor:
            print("❌ Editor harus dipilih.")
            return

        formatted_date = selected_date.strftime('%d-%m-%Y')
        print(f"DEBUG: Tanggal terformat: {formatted_date}")
        print(f"ℹ️ Mengirim entri: Tanggal '{formatted_date}', Jenis '{selected_type}', Editor '{selected_editor}'")

        try:
            # Prepare row data for leave/activity entry
            # The header order is: ["Judul", "Link", "Editor", "Upload", "Views", "Keterangan"]
            # For leave entries, we fill 'Upload' with the date and 'Keterangan' with the type.
            # 'Judul', 'Link', 'Views' are left empty or with default values.
            row_data_leave = ["", "", selected_editor, formatted_date, "", selected_type]
            print(f"DEBUG: Data baris yang akan dikirim: {row_data_leave}")

            # Append to VOD sheet
            ws_vod = None
            try:
                ws_vod = spreadsheet.worksheet("VOD")
            except gspread.exceptions.WorksheetNotFound:
                print(f"➕ Worksheet 'VOD' tidak ditemukan, membuat yang baru.")
                ws_vod = spreadsheet.add_worksheet("VOD", 1000, 10)
                ws_vod.append_row(["Judul","Link","Editor","Upload","Views","Keterangan"])
            except Exception as e:
                print(f"❌ Gagal mengakses/membuat worksheet VOD: {e}") # Corrected error message
                ws_vod = None

            if ws_vod is not None:
                try:
                    ws_vod.append_row(row_data_leave)
                    print("✅ Entri berhasil ditambahkan ke sheet 'VOD'.")
                except Exception as e:
                    print(f"❌ Gagal mengirim entri ke sheet 'VOD': {e}")

            # Append to SHORT sheet (optional, adjust if leave entries only go to one sheet)
            ws_short = None
            try:
                ws_short = spreadsheet.worksheet("SHORT")
            except gspread.exceptions.WorksheetNotFound:
                print(f"➕ Worksheet 'SHORT' tidak ditemukan, membuat yang baru.")
                ws_short = spreadsheet.add_worksheet("SHORT", 1000, 10)
                ws_short.append_row(["Judul","Link","Editor","Upload","Views","Keterangan"])
            except Exception as e:
                print(f"❌ Gagal mengakses/membuat worksheet SHORT: {e}") # Corrected error message
                ws_short = None

            if ws_short is not None:
                try:
                    ws_short.append_row(row_data_leave)
                    print("✅ Entri berhasil ditambahkan ke sheet 'SHORT'.")
                except Exception as e:
                    print(f"❌ Gagal mengirim entri ke sheet 'SHORT': {e}")

            print("\n🎉 Entri Hari Libur/Cuti/Kegiatan berhasil disimpan!")

        except Exception as e:
            print(f"❌ Gagal mengirim entri: {e}")

# New reset function for leave entry form
def reset_leave_form(b):
    leave_date_picker.value = datetime.now().date() # Reset to current date
    leave_type_dropdown.value = 'Libur' # Reset to default type
    leave_editor_dropdown.value = 'Erricson Bernedy S' # Reset editor to default
    leave_output.clear_output() # Clear any previous output

# ===============================
# Ikat Tombol dan Tampilkan UI (Perbarui Display)
# ===============================
process_btn.on_click(process_links)
reset_btn.on_click(reset_form)
leave_submit_btn.on_click(submit_leave_entry)
leave_reset_btn.on_click(reset_leave_form)

# Update the description of process_btn for its initial state
process_btn.description = "▶️ Kirim ke Sheet"

# Main Application Title
app_title = widgets.HTML('<h1 style="text-align: center; color: #1a73e8; font-size: 2.5em; font-weight: 600; margin-bottom: 20px;">YouTube Link & Leave Entry Automation</h1>', layout=widgets.Layout(width='auto'))

# Create a VBox for the link input section
link_input_vbox = widgets.VBox([
    widgets.HTML('<h3 style="font-size: 1.5em; font-weight: 500; text-align: left; margin-bottom: 10px;">Input Link YouTube</h3>'),
    link_count_display,
    input_links,
    live_preview_output,
    widgets.HBox([process_btn, reset_btn], layout=widgets.Layout(margin='10px 0 20px 0', justify_content='center')),
    output,
], layout=
    widgets.Layout(
    border='2px solid lightgray',
    padding='20px',
    margin='0 10px 0 0',
    width='auto',
    border_radius='8px'
))

# Create a VBox to group the new leave entry UI elements
leave_entry_vbox = widgets.VBox([
    widgets.HTML('<h3 style="font-size: 1.5em; font-weight: 500; text-align: left; margin-bottom: 10px;">Entri Hari Libur/Cuti/Kegiatan</h3>'),
    leave_date_picker,
    leave_type_dropdown,
    leave_editor_dropdown,
    widgets.HBox([leave_submit_btn, leave_reset_btn], layout=widgets.Layout(margin='10px 0 20px 0', justify_content='center', spacing='10px')),
    leave_output
], layout=widgets.Layout(padding='20px', border_radius='8px'))

# Wrap the leave entry UI in an Accordion
leave_entry_accordion = widgets.Accordion(children=[leave_entry_vbox], layout=widgets.Layout(width='auto', border='2px solid lightgray', padding='0', border_radius='8px'))
leave_entry_accordion.set_title(0, '--- Entri Hari Libur/Cuti/Kegiatan ---')

# Create an HBox to put the link input section and the leave entry section side-by-side
main_ui_hbox = widgets.HBox([
    link_input_vbox,
    leave_entry_accordion
], layout=widgets.Layout(justify_content='space-around', align_items='flex-start', flex_flow='row wrap', padding='10px', margin='10px 0'))

# Display the main UI HBox
display(app_title, main_ui_hbox)