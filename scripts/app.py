import streamlit as st
import pandas as pd
from catalog_manager import CatalogManager
import os
from pathlib import Path
# Initialize Manager
manager = CatalogManager()
# Page Config
st.set_page_config(page_title="Ridgemont Studio", page_icon="🎵", layout="wide")
# Title & Stats
st.title("🎵 Ridgemont Studio Manager")
# Sidebar Navigation
page = st.sidebar.radio("Go to", ["Dashboard", "All Songs", "Add Song", "Financials", "Pitching"])

if page == "Dashboard":
    st.header("Catalog Overview")

    # metrics
    summary = manager.get_catalog_summary()
    revenue = manager.get_revenue_summary()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Songs", summary['total_songs'])
    col2.metric("Total Revenue", f"${revenue['total_revenue']:,.2f}")
    act_name = max(summary['by_act'], key=summary['by_act'].get) if summary['by_act'] else "N/A"
    col3.metric("Top Act", act_name)

    st.subheader("Recent Songs")
    songs = manager.catalog['songs'][-10:]  # Show last 10
    if songs:
        df = pd.DataFrame(songs)
        cols = ['title', 'act_id', 'status', 'legacy_code']
        display_df = df[[c for c in cols if c in df.columns]]
        st.dataframe(display_df, use_container_width=True)

elif page == "All Songs":
    st.header("📀 Complete Catalog")

    songs = manager.catalog['songs']

    # Artist options - the three main bands
    artist_options = ["All", "Frozen Cloud", "Park Bellevue", "Bajan Sun"]
    # Also add any other artists found in catalog (like Honest Mile)
    other_artists = sorted(set(s.get('artist', '') for s in songs if s.get('artist') and s.get('artist') not in artist_options))
    artist_options.extend(other_artists)

    # Use a counter to force new widget keys when clearing
    if 'filter_version' not in st.session_state:
        st.session_state.filter_version = 0

    v = st.session_state.filter_version

    # Filters
    col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
    with col1:
        artist_filter = st.selectbox("Filter by Artist or Group", artist_options, key=f"artist_filter_{v}")
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "idea", "demo", "mixing", "mastered", "copyright", "released"], key=f"status_filter_{v}")
    with col3:
        search = st.text_input("Search by Title or Code", key=f"search_field_{v}")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄", help="Clear all filters"):
            st.session_state.filter_version += 1
            st.rerun()

    # Apply filters
    filtered = songs
    if artist_filter != "All":
        filtered = [s for s in filtered if s.get('artist') == artist_filter]
    if status_filter != "All":
        filtered = [s for s in filtered if s.get('status') == status_filter]
    if search:
        search_lower = search.lower()
        filtered = [s for s in filtered if search_lower in s.get('title', '').lower() or search_lower in s.get('legacy_code', '').lower()]

    # Display count
    st.write(f"**Showing {len(filtered)} of {len(songs)} songs**")

    # Group by publishing company tabs - with "All" option
    tab_all, tab_fc, tab_pb, tab_bs = st.tabs(["📋 All", "❄️ Frozen Cloud Music", "🏛️ Park Bellevue Collective", "☀️ Bajan Sun Publishing"])

    # Determine columns based on filter - include song_id and artist column
    if status_filter == "copyright":
        display_cols = ['song_id', 'legacy_code', 'title', 'artist', 'copyright_number']
        col_names = ['Song ID', 'Code', 'Title', 'Artist', 'Copyright #']
    else:
        display_cols = ['song_id', 'legacy_code', 'title', 'artist', 'status']
        col_names = ['Song ID', 'Code', 'Title', 'Artist', 'Status']

    def render_song_table(song_list, empty_msg):
        if song_list:
            df = pd.DataFrame(song_list)
            available_cols = [c for c in display_cols if c in df.columns]
            display_df = df[available_cols]
            col_labels = [col_names[display_cols.index(c)] for c in available_cols]
            display_df.columns = col_labels
            st.dataframe(display_df, use_container_width=True, height=400)
            st.caption(f"{len(song_list)} songs")
        else:
            st.info(empty_msg)

    with tab_all:
        render_song_table(filtered, "No songs match filters")

    with tab_fc:
        fc_songs = [s for s in filtered if s.get('act_id') == 'FROZEN_CLOUD']
        render_song_table(fc_songs, "No Frozen Cloud Music songs match filters")

    with tab_pb:
        pb_songs = [s for s in filtered if s.get('act_id') == 'PARK_BELLEVUE']
        render_song_table(pb_songs, "No Park Bellevue Collective songs match filters")

    with tab_bs:
        bs_songs = [s for s in filtered if s.get('act_id') == 'BAJAN_SUN']
        render_song_table(bs_songs, "No Bajan Sun Publishing songs match filters")

elif page == "Add Song":
    st.header("New Song Entry")

    # Publishing company mapping
    PUBLISHER_MAP = {
        "Frozen Cloud Music": "FROZEN_CLOUD",
        "Park Bellevue Collective": "PARK_BELLEVUE",
        "Bajan Sun Publishing": "BAJAN_SUN"
    }

    # Get unique artists from catalog for suggestions
    existing_artists = sorted(set(s.get('artist', '') for s in manager.catalog['songs'] if s.get('artist')))

    # Get existing song titles for cover selection (unique, sorted)
    existing_songs = sorted(set(s['title'] for s in manager.catalog['songs']))

    with st.form("new_song_form"):
        title = st.text_input("Song Title")

        # Text input for artist with suggestions shown below
        artist = st.text_input("Artist or Group", placeholder="e.g., Frozen Cloud, Echoes of Jahara")
        if existing_artists:
            st.caption(f"Existing artists: {', '.join(existing_artists)}")

        publisher_label = st.selectbox("Publishing Company", list(PUBLISHER_MAP.keys()))
        publisher_id = PUBLISHER_MAP[publisher_label]
        status = st.selectbox("Status", ["idea", "demo", "mixing", "mastered", "copyright", "released"])

        # Cover song selection
        st.markdown("---")
        is_cover = st.checkbox("This is a cover song")
        cover_of = st.selectbox("Song Covered", ["(Select original song)"] + existing_songs, help="Select the original song being covered")

        submitted = st.form_submit_button("Create Song")

        if submitted:
            if not title:
                st.error("❌ Please enter a song title")
            elif not artist:
                st.error("❌ Please enter an artist or group name")
            elif is_cover and (not cover_of or cover_of == "(Select original song)"):
                st.error("❌ Please select the song being covered")
            else:
                result = manager.add_song(
                    title,
                    publisher_id,
                    status=status,
                    is_cover=is_cover,
                    cover_of=cover_of if (is_cover and cover_of and cover_of != "(Select original song)") else None,
                    artist=artist
                )
                if isinstance(result, str) and result.startswith("❌"):
                    st.error(result)
                else:
                    if is_cover:
                        st.success(f"✅ Added cover '{title}' by {artist} ({publisher_label})")
                    else:
                        code_msg = f" (Code: {result.get('legacy_code', '')})" if isinstance(result, dict) else ""
                        st.success(f"✅ Added '{title}' by {artist} ({publisher_label}){code_msg}")

elif page == "Financials":
    st.header("💰 CFO Module")

    tab1, tab2 = st.tabs(["Log Expense", "Forecast"])

    with tab1:
        st.subheader("Log an Expense")
        if manager.catalog['songs']:
            titles = [s['title'] for s in manager.catalog['songs']]
            with st.form("expense_form"):
                song_title = st.selectbox("Select Song", titles)
                amount = st.number_input("Amount ($)", min_value=0.0, step=10.0)
                reason = st.text_input("Reason (e.g. Mixing, Musicians)")
                submitted = st.form_submit_button("Log Expense")

                if submitted:
                    msg = manager.add_expense_shortcode(song_title, amount, reason)
                    st.success(msg)

    with tab2:
        st.subheader("Royalty Forecaster")
        if manager.catalog['songs']:
            titles = [s['title'] for s in manager.catalog['songs']]
            f_title = st.selectbox("Song to Forecast", titles, key="forecast_song")
            streams = st.number_input("Projected Streams", min_value=1000, step=1000)
            if st.button("Run Simulation"):
                result = manager.simulate_royalties(f_title, str(int(streams)))
                st.info(result)

elif page == "Pitching":
    st.header("🚀 Pitch Engine")
    if manager.catalog['songs']:
        titles = [s['title'] for s in manager.catalog['songs']]

        with st.form("pitch_form"):
            song = st.selectbox("Song to Pitch", titles)
            supervisor = st.text_input("Supervisor Name")
            submitted = st.form_submit_button("Generate Pitch")

            if submitted and supervisor:
                result = manager.execute_pitch_shortcode(song, supervisor)
                st.markdown(result)
