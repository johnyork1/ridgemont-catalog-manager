import streamlit as st
import pandas as pd
from catalog_manager import CatalogManager
import os
from pathlib import Path
# Initialize Manager
manager = CatalogManager()
# Page Config
st.set_page_config(page_title="Ridgemont Studio", page_icon="🎵", layout="wide")
# Logo and Title
col_logo, col_title = st.columns([0.5, 5])
with col_logo:
    st.image(str(Path(__file__).parent.parent / "logo.jpeg"), width=80)
with col_title:
    st.markdown("<h1 style='margin-top: 10px;'>Ridgemont Studio Manager</h1>", unsafe_allow_html=True)
# Sidebar Navigation (with key for programmatic control)
# Initialize nav_page in session state if not set
if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "Dashboard"

# Get the list of pages
NAV_PAGES = ["Dashboard", "All Songs", "Albums", "Add Song", "Edit Song", "View Deployments", "Financials", "Pitching"]

# Find index of current page
nav_index = NAV_PAGES.index(st.session_state.nav_page) if st.session_state.nav_page in NAV_PAGES else 0

page = st.sidebar.radio("Go to", NAV_PAGES, index=nav_index, key="nav_page")

if page == "Dashboard":
    st.header("Catalog Overview")

    # metrics
    summary = manager.get_catalog_summary()
    revenue = manager.get_revenue_summary()

    # Top row metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Songs", summary['total_songs'])
    col2.metric("Total Revenue", f"${revenue['total_revenue']:,.2f}")
    act_name = max(summary['by_act'], key=summary['by_act'].get) if summary['by_act'] else "N/A"
    col3.metric("Top Act", act_name.replace('_', ' ').title() if act_name != "N/A" else "N/A")

    # Songs by Publisher
    st.subheader("Songs by Publisher")
    pub_col1, pub_col2, pub_col3 = st.columns(3)
    pub_col1.metric("❄️ Frozen Cloud", summary['by_act'].get('FROZEN_CLOUD', 0))
    pub_col2.metric("🏛️ Park Bellevue", summary['by_act'].get('PARK_BELLEVUE', 0))
    pub_col3.metric("☀️ Bajan Sun", summary['by_act'].get('BAJAN_SUN', 0))

    st.markdown("---")
    st.subheader("Recent Songs")
    songs = manager.catalog['songs'][-10:]  # Show last 10
    if songs:
        # Flatten data for display with deployment info
        table_data = []
        for s in songs:
            deps = s.get('deployments', {})
            reg = s.get('registration', {})
            dist = ", ".join(deps.get('distribution', [])) or "-"
            sync = ", ".join(deps.get('sync_libraries', [])) or "-"
            isrc = reg.get('isrc', '-') or '-'
            table_data.append({
                "Title": s['title'],
                "Artist": s.get('artist', '-'),
                "Publisher": s.get('act_id', '-').replace('_', ' ').title(),
                "Status": s['status'],
                "ISRC": isrc,
                "Distributor": dist
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)

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

elif page == "Albums":
    st.header("💿 Albums")

    albums = manager.catalog.get('albums', [])

    if not albums:
        st.info("No albums in catalog yet.")
    else:
        for album in albums:
            with st.expander(f"**{album['title']}** — {album['artist']}", expanded=True):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Artist:** {album['artist']}")
                    st.markdown(f"**Status:** {album.get('status', 'Unknown').replace('_', ' ').title()}")
                    if album.get('release_date'):
                        st.markdown(f"**Release Date:** {album['release_date']}")
                    if album.get('notes'):
                        st.markdown(f"**Notes:** {album['notes']}")

                with col2:
                    st.markdown(f"**Album ID:** `{album['album_id']}`")
                    st.markdown(f"**Act:** {album.get('act_id', 'Unknown').replace('_', ' ').title()}")

                # Track listing
                tracks = album.get('tracks', [])
                if tracks:
                    st.markdown("---")
                    st.markdown("**Track Listing:**")
                    track_data = []
                    for t in tracks:
                        # Look up song details
                        song = next((s for s in manager.catalog['songs'] if s['song_id'] == t['song_id']), None)
                        status = song.get('status', '-') if song else '-'
                        track_data.append({
                            "#": t['track_number'],
                            "Title": t['title'],
                            "Song ID": t['song_id'],
                            "Status": status.title()
                        })
                    st.dataframe(pd.DataFrame(track_data), use_container_width=True, hide_index=True)
                else:
                    st.caption("No tracks added yet.")

    # Add New Album section
    st.markdown("---")
    st.subheader("➕ Add New Album")

    # Get unique artists
    existing_artists = sorted(set(s.get('artist', '') for s in manager.catalog['songs'] if s.get('artist')))

    with st.form("new_album_form"):
        album_title = st.text_input("Album Title")
        album_artist = st.text_input("Artist", placeholder="e.g., Stone Meridian")
        if existing_artists:
            st.caption(f"Existing artists: {', '.join(existing_artists)}")

        # Act selection
        ACT_MAP = {
            "Frozen Cloud Music": "FROZEN_CLOUD",
            "Park Bellevue Collective": "PARK_BELLEVUE",
            "Bajan Sun Publishing": "BAJAN_SUN",
            "Stone Meridian": "STONE_MERIDIAN"
        }
        act_label = st.selectbox("Publishing Act", list(ACT_MAP.keys()))

        album_status = st.selectbox("Status", ["in_progress", "mixing", "mastered", "released"])
        album_notes = st.text_area("Notes", placeholder="Optional notes about the album...")

        submitted = st.form_submit_button("Create Album")

        if submitted:
            if not album_title:
                st.error("❌ Please enter an album title")
            elif not album_artist:
                st.error("❌ Please enter an artist name")
            else:
                from datetime import datetime
                new_album = {
                    "album_id": f"ALB-{str(len(albums) + 1).zfill(4)}",
                    "title": album_title,
                    "artist": album_artist,
                    "act_id": ACT_MAP[act_label],
                    "release_date": None,
                    "status": album_status,
                    "tracks": [],
                    "artwork": None,
                    "notes": album_notes,
                    "created": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat()
                }

                if 'albums' not in manager.catalog:
                    manager.catalog['albums'] = []
                manager.catalog['albums'].append(new_album)
                manager.save_catalog()
                st.success(f"✅ Created album '{album_title}' by {album_artist}")
                st.rerun()

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

        # Deployment Strategy
        st.markdown("---")
        st.subheader("🚀 Deployment Strategy")
        dists = st.multiselect("Distribution", ["DistroKid", "TuneCore", "CD Baby", "Amuse"])
        syncs = st.multiselect("Sync Libraries", ["Songtradr", "Music Gateway", "Pond5", "Disco", "Taxi"])
        streams = st.multiselect("Live On", ["Spotify", "Apple Music", "Amazon", "YouTube", "Tidal"])

        submitted = st.form_submit_button("Create Song")

        if submitted:
            if not title:
                st.error("❌ Please enter a song title")
            elif not artist:
                st.error("❌ Please enter an artist or group name")
            elif is_cover and (not cover_of or cover_of == "(Select original song)"):
                st.error("❌ Please select the song being covered")
            else:
                deployments = {
                    "distribution": dists,
                    "sync_libraries": syncs,
                    "streaming": streams
                }
                result = manager.add_song(
                    title,
                    publisher_id,
                    status=status,
                    is_cover=is_cover,
                    cover_of=cover_of if (is_cover and cover_of and cover_of != "(Select original song)") else None,
                    artist=artist,
                    deployments=deployments
                )
                if isinstance(result, str) and result.startswith("❌"):
                    st.error(result)
                else:
                    if is_cover:
                        st.success(f"✅ Added cover '{title}' by {artist} ({publisher_label})")
                    else:
                        code_msg = f" (Code: {result.get('legacy_code', '')})" if isinstance(result, dict) else ""
                        st.success(f"✅ Added '{title}' by {artist} ({publisher_label}){code_msg}")

# --- IMPROVED EDIT SONG TAB ---
elif page == "Edit Song":
    st.header("Update Song Details")

    if not manager.catalog['songs']:
        st.warning("No songs in catalog.")
    else:
        # 1. Smart Selector with disambiguation for duplicates/covers
        # Build display labels: "Title | Artist (Act)" to distinguish covers
        song_options = {}
        for s in manager.catalog['songs']:
            act_name = s.get('act_id', 'Unknown').replace('_', ' ').title()
            artist = s.get('artist', act_name)
            # Create unique display label
            display_label = f"{s['title']} | {artist}"
            # Handle duplicates by adding song_id suffix if needed
            if display_label in song_options:
                display_label = f"{s['title']} | {artist} ({s['song_id']})"
            song_options[display_label] = s['song_id']

        # Sort options alphabetically by title
        sorted_options = sorted(song_options.keys())

        # Initialize session state for last selection
        if 'last_selected_song_id' not in st.session_state:
            st.session_state.last_selected_song_id = None

        def update_selection():
            if st.session_state.song_selector:
                st.session_state.last_selected_song_id = song_options.get(st.session_state.song_selector)

        # Find default index if we have a previous selection
        default_index = None
        if st.session_state.last_selected_song_id:
            for i, label in enumerate(sorted_options):
                if song_options[label] == st.session_state.last_selected_song_id:
                    default_index = i
                    break

        selected_label = st.selectbox(
            "Select Song to Edit",
            sorted_options,
            index=default_index,
            placeholder="Type to search...",
            key="song_selector",
            on_change=update_selection
        )

        # Get current data fresh from the manager using song_id
        selected_song = None
        if selected_label:
            song_id = song_options[selected_label]
            selected_song = next((s for s in manager.catalog['songs'] if s['song_id'] == song_id), None)

        if selected_song:
            song_id = selected_song['song_id']
            current_deps = selected_song.get('deployments', {})
            current_reg = selected_song.get('registration', {})

            # 2. The Edit Form
            with st.form("edit_song_form"):
                st.subheader(f"Editing: {selected_song['title']}")

                col1, col2 = st.columns(2)
                new_status = col1.selectbox("Status",
                                        ["idea", "demo", "mixing", "mastered", "released"],
                                        index=["idea", "demo", "mixing", "mastered", "released"].index(selected_song['status']) if selected_song['status'] in ["idea", "demo", "mixing", "mastered", "released"] else 0)

                st.markdown("### 📝 Registration Info")
                c1, c2 = st.columns(2)
                isrc = c1.text_input("ISRC", value=current_reg.get('isrc', '') or '')
                iswc = c2.text_input("ISWC", value=current_reg.get('iswc', '') or '')

                st.markdown("### 🚀 Deployment Strategy")
                # Use default=[] to pre-fill the boxes with saved data
                dists = st.multiselect("Distribution", ["DistroKid", "TuneCore", "CD Baby", "Amuse", "AWAL", "Ditto"],
                                     default=current_deps.get('distribution', []))

                syncs = st.multiselect("Sync Libraries", ["Songtradr", "Music Gateway", "Pond5", "Disco", "Taxi", "Musicbed", "Artlist"],
                                     default=current_deps.get('sync_libraries', []))

                streams = st.multiselect("Live On", ["Spotify", "Apple Music", "Amazon", "YouTube", "Tidal", "Deezer", "Pandora"],
                                       default=current_deps.get('streaming', []))

                save_changes = st.form_submit_button("💾 Save Changes")

                if save_changes:
                    # Construct the update packet
                    updates = {
                        "status": new_status,
                        "registration": {
                            "isrc": isrc,
                            "iswc": iswc
                        },
                        "deployments": {
                            "distribution": dists,
                            "sync_libraries": syncs,
                            "streaming": streams
                        }
                    }

                    # 1. Write to Disk
                    success = manager.update_song(song_id, updates)

                    if success:
                        st.success(f"✅ Saved changes to {selected_song['title']}!")

                        # 2. WAIT for file system (The Magic Fix)
                        import time
                        time.sleep(0.5)

                        # 3. Reload Page
                        st.rerun()
                    else:
                        st.error("❌ Error saving to file. Check terminal for details.")

# --- VIEW DEPLOYMENTS PAGE ---
elif page == "View Deployments":
    st.header("🚀 Deployment Overview")
    st.caption("See where your songs are distributed and streaming")

    songs = manager.catalog['songs']

    # Publisher mapping (legal entities)
    PUBLISHER_MAP = {
        "FROZEN_CLOUD": "Frozen Cloud Music",
        "PARK_BELLEVUE": "Park Bellevue Collective",
        "BAJAN_SUN": "Bajan Sun Publishing"
    }

    # All platform options
    ALL_DISTRIBUTORS = ["DistroKid", "TuneCore", "CD Baby", "Amuse", "AWAL", "Ditto"]
    ALL_SYNC_LIBS = ["Songtradr", "Music Gateway", "Pond5", "Disco", "Taxi", "Musicbed", "Artlist"]
    ALL_STREAMING = ["Spotify", "Apple Music", "Amazon", "YouTube", "Tidal", "Deezer", "Pandora"]
    ALL_PLATFORMS = ALL_DISTRIBUTORS + ALL_SYNC_LIBS + ALL_STREAMING

    # Get unique publishers from catalog
    ALL_PUBLISHERS = sorted(set(PUBLISHER_MAP.get(s.get('act_id', ''), 'Unknown') for s in songs))

    # Filters Row 1: Publisher
    selected_publishers = st.multiselect(
        "Filter by Publisher",
        ALL_PUBLISHERS,
        help="Select one or more publishers to filter songs"
    )

    # Filters Row 2: Platform and Match Mode
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_platforms = st.multiselect(
            "Filter by Platform",
            ALL_PLATFORMS,
            help="Select one or more platforms to filter songs"
        )
    with col2:
        match_mode = st.radio("Match Mode", ["Any (OR)", "All (AND)"], horizontal=True)

    # Apply publisher filter first
    if selected_publishers:
        filtered_songs = [s for s in songs if PUBLISHER_MAP.get(s.get('act_id', ''), 'Unknown') in selected_publishers]
    else:
        filtered_songs = songs

    # Apply platform filters
    if selected_platforms:
        platform_filtered = []
        for s in filtered_songs:
            deps = s.get('deployments', {})
            song_platforms = (
                deps.get('distribution', []) +
                deps.get('sync_libraries', []) +
                deps.get('streaming', [])
            )

            if match_mode == "Any (OR)":
                # Song has at least ONE of the selected platforms
                if any(p in song_platforms for p in selected_platforms):
                    platform_filtered.append(s)
            else:
                # Song has ALL of the selected platforms
                if all(p in song_platforms for p in selected_platforms):
                    platform_filtered.append(s)
        filtered_songs = platform_filtered

    st.write(f"**Showing {len(filtered_songs)} of {len(songs)} songs**")

    # Build the table with emoji indicators
    if filtered_songs:
        table_data = []
        song_id_map = {}  # Map row index to song data for jump-to-edit
        for idx, s in enumerate(filtered_songs):
            deps = s.get('deployments', {})
            dist_list = deps.get('distribution', [])
            sync_list = deps.get('sync_libraries', [])
            stream_list = deps.get('streaming', [])

            # Format with checkmarks for selected platforms
            def format_platforms(platforms, all_options):
                if not platforms:
                    return "-"
                result = []
                for p in platforms:
                    if selected_platforms and p in selected_platforms:
                        result.append(f"✅ {p}")
                    else:
                        result.append(p)
                return ", ".join(result)

            # Get publisher from mapping
            act_id = s.get('act_id', '')
            publisher = PUBLISHER_MAP.get(act_id, 'Unknown')
            artist = s.get('artist', act_id.replace('_', ' ').title())

            table_data.append({
                "Title": s['title'],
                "Artist": artist,
                "Publisher": publisher,
                "Status": s.get('status', '-').title(),
                "Distributors": format_platforms(dist_list, ALL_DISTRIBUTORS),
                "Sync Libraries": format_platforms(sync_list, ALL_SYNC_LIBS),
                "Streaming": format_platforms(stream_list, ALL_STREAMING)
            })

            # Store mapping for jump-to-edit
            song_id_map[idx] = {
                'title': s['title'],
                'artist': artist,
                'song_id': s['song_id']
            }

        # Display table with row selection
        df = pd.DataFrame(table_data)
        selection = st.dataframe(
            df,
            use_container_width=True,
            height=500,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Jump to Edit button if a row is selected
        if selection and selection.selection and selection.selection.rows:
            selected_row_idx = selection.selection.rows[0]
            if selected_row_idx in song_id_map:
                selected_info = song_id_map[selected_row_idx]
                # Build the smart key to match Edit Song dropdown format
                smart_key = f"{selected_info['title']} | {selected_info['artist']}"

                st.markdown("---")
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(f"✏️ Edit '{selected_info['title']}'", type="primary"):
                        # Pre-select the song in Edit Song page
                        st.session_state.last_selected_song_id = selected_info['song_id']
                        st.session_state.nav_page = "Edit Song"
                        st.rerun()
                with col2:
                    st.caption(f"Selected: **{smart_key}**")

        # Summary stats
        st.markdown("---")
        st.subheader("📊 Platform Summary")

        # Count songs per platform
        platform_counts = {}
        for s in songs:
            deps = s.get('deployments', {})
            all_plats = deps.get('distribution', []) + deps.get('sync_libraries', []) + deps.get('streaming', [])
            for p in all_plats:
                platform_counts[p] = platform_counts.get(p, 0) + 1

        if platform_counts:
            # Display in columns
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**📦 Distribution**")
                for p in ALL_DISTRIBUTORS:
                    count = platform_counts.get(p, 0)
                    if count > 0:
                        st.write(f"✅ {p}: {count} songs")
                    else:
                        st.write(f"⬜ {p}: 0 songs")

            with col2:
                st.markdown("**🎬 Sync Libraries**")
                for p in ALL_SYNC_LIBS:
                    count = platform_counts.get(p, 0)
                    if count > 0:
                        st.write(f"✅ {p}: {count} songs")
                    else:
                        st.write(f"⬜ {p}: 0 songs")

            with col3:
                st.markdown("**🎧 Streaming**")
                for p in ALL_STREAMING:
                    count = platform_counts.get(p, 0)
                    if count > 0:
                        st.write(f"✅ {p}: {count} songs")
                    else:
                        st.write(f"⬜ {p}: 0 songs")
    else:
        st.info("No songs match the selected platforms.")

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
