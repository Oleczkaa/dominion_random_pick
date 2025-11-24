import sqlite3
import streamlit as st
import pandas as pd

# -------------------------
# Database connection
# -------------------------
DB = "dominion.db"
conn = sqlite3.connect(DB)

# -------------------------
# Session State Init
# -------------------------
if "kingdom" not in st.session_state:
    st.session_state.kingdom = None

if "filters" not in st.session_state:
    st.session_state.filters = None


# -------------------------
# UI Title
# -------------------------
st.title("Dominion Kingdom Generator")

# -------------------------
# Load sets and types
# -------------------------
excluded_types = ['Event', 'Curse']

excluded_card_names = [
    'Copper', 'Silver', 'Gold',
    'Estate', 'Duchy', 'Province', 'Gardens',
    'Colony', 'Curse', 'Platinum'
]

df_sets = pd.read_sql_query("SELECT DISTINCT set_name FROM card_sets ORDER BY set_name", conn)
df_types = pd.read_sql_query("SELECT DISTINCT type FROM card_types ORDER BY type", conn)

all_sets = sorted(df_sets["set_name"].tolist())
all_types = sorted([t for t in df_types["type"].tolist() if t not in excluded_types])


# -------------------------
# Function: base query builder
# -------------------------
def build_query(selected_sets, selected_types, excluded_ids=None, limit=None):
    query = """
    SELECT DISTINCT c.id, c.name, c.types, c.cost, cs.set_name, c.text
    FROM cards c
    JOIN card_sets cs ON c.id = cs.card_id
    JOIN card_types ct ON c.id = ct.card_id
    WHERE 1=1
    AND c.id NOT IN (
        SELECT card_id FROM card_types
        WHERE type IN ({}))
    """.format(",".join(["?"] * len(excluded_types)))

    params = excluded_types.copy()

    # Excluded card names
    if excluded_card_names:
        query += " AND c.name NOT IN ({})".format(",".join(["?"] * len(excluded_card_names)))
        params += excluded_card_names

    # Filter by set
    if selected_sets:
        query += " AND cs.set_name IN ({})".format(",".join(["?"] * len(selected_sets)))
        params += selected_sets

    # Filter by selected card types
    if selected_types:
        query += """
        AND c.id IN (
            SELECT card_id FROM card_types
            WHERE type IN ({}))
        """.format(",".join(["?"] * len(selected_types)))
        params += selected_types

    # Exclude specific IDs (important when reshuffling)
    if excluded_ids:
        query += " AND c.id NOT IN ({})".format(",".join(["?"] * len(excluded_ids)))
        params += excluded_ids

    # Randomize & limit if needed
    query += " ORDER BY RANDOM()"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    return query, params


# -------------------------
# Function: generate new kingdom
# -------------------------
def generate_kingdom(selected_sets, selected_types, num_cards):
    query, params = build_query(selected_sets, selected_types, limit=num_cards)
    return pd.read_sql_query(query, conn, params=params)


# -------------------------
# Function: reshuffle one card
# -------------------------
def reshuffle_card(idx):
    kingdom = st.session_state.kingdom
    filters = st.session_state.filters

    # IDs of all other cards (prevent duplicates)
    remaining_ids = kingdom.drop(idx)["id"].tolist()

    # Fetch one replacement card
    query, params = build_query(
        filters["selected_sets"],
        filters["selected_types"],
        excluded_ids=remaining_ids,
        limit=1
    )
    replacement = pd.read_sql_query(query, conn, params=params)

    # Replace the card at the SAME index
    kingdom.loc[idx] = replacement.iloc[0]

    st.session_state.kingdom = kingdom


# -------------------------
# Filters UI
# -------------------------
preselected_sets = ["Base", "Prosperity", "Plunder"]  # change to your desired expansions
selected_sets = st.multiselect(
    "Choose expansions:",
    options=all_sets,
    default=preselected_sets
)


selected_types = st.multiselect("Choose card types:", all_types)
num_cards = st.slider("How many cards do you want?", 1, 15, 10)

# -------------------------
# Generate Button
# -------------------------
if st.button("Generate Kingdom"):
    st.session_state.filters = {
        "selected_sets": selected_sets,
        "selected_types": selected_types,
        "num_cards": num_cards
    }

    st.session_state.kingdom = generate_kingdom(selected_sets, selected_types, num_cards)
    st.rerun()  # Important: stabilizes the session state


# -------------------------
# Display Kingdom + Reshuffle Buttons
# -------------------------
if st.session_state.kingdom is not None:
    st.subheader("🎴 Generated Kingdom")

    df = st.session_state.kingdom

    # Table of all cards
    st.data_editor(
        df[["name", "types", "set_name", "cost", "text"]],
        column_config={"text": st.column_config.TextColumn("Card Text", max_chars=1800)},
        hide_index=True,
        use_container_width=True
    )

    st.markdown("### Card List (click 🔄 to reshuffle one):")

    for idx, row in df.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"- **{row['name']}** — *{row['set_name']}* ({row['types']})")

        with col2:
            if st.button("🔄", key=f"reshuffle_{idx}"):
                reshuffle_card(idx)
                st.rerun()


# Close DB when Streamlit stops
conn.close()
