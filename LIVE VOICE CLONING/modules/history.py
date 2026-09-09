import os
import json
import pandas as pd
import streamlit as st

HISTORY_FILE = "data/history.json"

def load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history_data: list):
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=4)

def log_translation_event(module: str, source_text: str, translated_text: str, target_lang: str, has_audio: bool = False):
    import datetime
    history = load_history()
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "module": module,
        "source_text": source_text,
        "translated_text": translated_text,
        "target_lang": target_lang,
        "has_audio": has_audio
    }
    history.insert(0, entry) # latest first
    save_history(history)
    # increment session stats
    st.session_state["total_translations_count"] = st.session_state.get("total_translations_count", 0) + 1

def render_history_module():
    """
    Module 5: Translation & Audio Logs History
    """
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.markdown('<h2 class="orbitron-text">📜 TRANSLATION & AUDIO HISTORY</h2>', unsafe_allow_html=True)
    st.write("Review, filter, and export past neural voice translations and transcript records.")

    history = load_history()

    if not history:
        st.info("No translation history logged yet in this session.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            modules_list = ["All Modules"] + list(set([h["module"] for h in history]))
            selected_mod = st.selectbox("Filter by Module", modules_list)

        with col_f2:
            search_query = st.text_input("Search Transcript Keywords", placeholder="Type to filter...")

        filtered = history
        if selected_mod != "All Modules":
            filtered = [h for h in filtered if h["module"] == selected_mod]

        if search_query.strip():
            q = search_query.lower()
            filtered = [h for h in filtered if q in h["source_text"].lower() or q in h["translated_text"].lower()]

        st.markdown(f"##### Showing {len(filtered)} Records")

        # Convert to Pandas dataframe for table view
        df = pd.DataFrame(filtered)
        if not df.empty:
            st.dataframe(
                df[["timestamp", "module", "source_text", "translated_text", "target_lang"]],
                use_container_width=True
            )

        st.markdown("---")
        st.markdown("### 📥 Export & Data Tools")

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            json_str = json.dumps(history, indent=4)
            st.download_button(
                label="💾 DOWNLOAD FULL TRANSCRIPT LOGS (JSON)",
                data=json_str,
                file_name="translation_history.json",
                mime="application/json"
            )
        with col_ex2:
            if st.button("🗑️ CLEAR HISTORY LOGS"):
                save_history([])
                st.session_state["total_translations_count"] = 0
                st.success("Translation history cleared.")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
