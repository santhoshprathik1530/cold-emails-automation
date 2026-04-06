import streamlit as st
import pandas as pd
import requests
import os
import time
import threading
import tempfile
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Apollo + Dashboard Hub", page_icon="🔗", layout="wide")


def send_to_n8n(webhook_url, df, filename=None):
    if not webhook_url:
        st.error("Provide a valid n8n webhook URL")
        return False
    payload = {"filename": filename or "uploaded.csv", "rows": df.to_dict(orient="records")}
    try:
        r = requests.post(webhook_url, json=payload, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Failed to trigger n8n: {e}")
        return False


def upload_to_sheet_from_file(df, creds_path, sheet_id):
    try:
        import gspread
        from gspread_dataframe import set_with_dataframe
    except Exception as e:
        st.error(f"Missing gspread packages: {e}")
        return False
    gc = gspread.service_account(filename=creds_path)
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1
    ws.clear()
    set_with_dataframe(ws, df, include_index=False, include_column_header=True)
    return True


def poll_downloads(process_fn, poll_dir=None, interval=5):
    poll_dir = poll_dir or os.path.expanduser("~/Downloads")
    last_mtime = 0
    while True:
        try:
            files = [os.path.join(poll_dir, f) for f in os.listdir(poll_dir) if f.lower().endswith('.csv')]
            if files:
                newest = max(files, key=os.path.getmtime)
                mtime = os.path.getmtime(newest)
                if mtime > last_mtime:
                    logging.info(f"Found new CSV: {newest}")
                    process_fn(newest)
                    last_mtime = mtime
        except Exception as e:
            logging.error(f"Poll error: {e}")
        time.sleep(interval)


def main():
    st.title("Apollo + Dashboard Hub")

    tab = st.tabs(["Uploader", "Dashboard"])

    # ---- Uploader tab ----
    with tab[0]:
        st.markdown("### CSV Upload & n8n Trigger")

        uploaded = st.file_uploader("Upload CSV file from Apollo (or drag & drop)", type=["csv"], accept_multiple_files=False)
        webhook = st.text_input("Local n8n webhook URL", value="http://localhost:5678/webhook/your-webhook")

        st.markdown("---")
        st.markdown("**Google Sheets (optional)** — provide service account JSON and Sheet ID to push CSV there.")
        creds_file = st.file_uploader("Service account JSON (optional)", type=["json"], key="sa_json")
        sheet_id = st.text_input("Google Sheet ID (optional)")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Preview CSV") and uploaded is not None:
                df = pd.read_csv(uploaded)
                st.dataframe(df.head(200))
        with col2:
            if st.button("Send to n8n") and uploaded is not None:
                uploaded.seek(0)
                df = pd.read_csv(uploaded)
                ok = send_to_n8n(webhook, df, filename=getattr(uploaded, 'name', 'upload.csv'))
                if ok:
                    st.success("Sent to n8n successfully")

        st.markdown("---")
        if st.button("Upload to Google Sheet"):
            if uploaded is None:
                st.error("Upload a CSV first")
            elif creds_file is None or not sheet_id:
                st.error("Provide service account JSON and Sheet ID")
            else:
                # write creds to temp file
                tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
                tf.write(creds_file.getvalue())
                tf.flush(); tf.close()
                uploaded.seek(0)
                df = pd.read_csv(uploaded)
                ok = upload_to_sheet_from_file(df, tf.name, sheet_id)
                if ok:
                    st.success("Uploaded to Google Sheet")

        st.markdown("---")
        st.markdown("### Auto-watch Downloads (optional)")
        watch = st.checkbox("Start auto-watch of ~/Downloads and auto-send new CSVs to n8n", key="auto_watch")
        if watch and "watch_thread" not in st.session_state:
            def process_path(path):
                try:
                    df = pd.read_csv(path)
                    send_to_n8n(webhook, df, filename=os.path.basename(path))
                except Exception as e:
                    logging.error(f"Process file error: {e}")

            t = threading.Thread(target=poll_downloads, args=(process_path,), daemon=True)
            t.start()
            st.session_state.watch_thread = True
            st.info("Auto-watch started in background")
        if not watch and st.session_state.get("watch_thread"):
            st.session_state.pop("watch_thread", None)
            st.info("Auto-watch flag cleared (thread may still run until process exit)")

    # ---- Dashboard tab ----
    with tab[1]:
        st.markdown("### Hunt Tracker (Dashboard)")
        try:
            SB_URL = st.secrets.get("supabase_url")
            SB_KEY = st.secrets.get("supabase_key")
        except Exception:
            SB_URL = None; SB_KEY = None

        if not SB_URL or not SB_KEY:
            st.warning("Supabase credentials missing in Streamlit secrets — dashboard will not show live data.")
        else:
            try:
                res = requests.get(f"{SB_URL}/rest/v1/email_tracking?select=*&order=sent_at.desc", headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    df = pd.DataFrame(data)
                    df["sent_at"] = pd.to_datetime(df.get("sent_at"), errors="coerce")
                    st.dataframe(df.head(200))
                else:
                    st.error(f"Supabase error: {res.status_code} {res.text}")
            except Exception as e:
                st.error(f"Failed to fetch dashboard data: {e}")


if __name__ == "__main__":
    main()
