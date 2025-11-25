# Dominion Kingdom Generator Web App
#
# This Streamlit app helps users generate a random set ("kingdom") of cards for the board game Dominion.
# Users can filter which expansions (sets) and card types to include, then generate a kingdom of cards
# matching those filters. Each card in the kingdom can be reshuffled individually for more variety.
#
# Data Source:
#   - Card information is originally sourced from "cards.json" and imported into the SQLite database.
#   - Card details are stored in a SQLite database 'dominion.db', with tables for cards, card_types, and card_sets.
#
# Features:
#   - Select expansions (sets) and card types as filters.
#   - Generate a random kingdom of cards based on selected filters.
#   - Reshuffle individual cards in the generated kingdom.
#
# Notes:
#   - This project is designed for beginners learning programmin, Python, SQL, and Streamlit.
#   - The code is written to be clear and well-commented for educational purposes.
#

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
def build_query(
    selected_sets, 
    selected_types, 
    excluded_ids=None, 
    limit=None, 
    extra_conditions="", 
    excluded_types=None, 
    excluded_card_names=None
):
    if excluded_types is None:
        excluded_types = []
    if excluded_card_names is None:
        excluded_card_names = []

    query = """
    SELECT DISTINCT c.id, c.name, c.types, c.cost, cs.set_name, c.text
    FROM cards c
    JOIN card_sets cs ON c.id = cs.card_id
    JOIN card_types ct ON c.id = ct.card_id
    WHERE 1=1
    """
    params = []

    # Filter by selected sets (expansions)
    if selected_sets:
        query += " AND cs.set_name IN ({})".format(
            ",".join(["?"] * len(selected_sets))
        )
        params += selected_sets

    # Exclude types
    if excluded_types:
        query += " AND c.id NOT IN (SELECT card_id FROM card_types WHERE type IN ({}))".format(
            ",".join(["?"] * len(excluded_types))
        )
        params += excluded_types

    # Exclude specific card names
    if excluded_card_names:
        query += " AND c.name NOT IN ({})".format(",".join(["?"] * len(excluded_card_names)))
        params += excluded_card_names

    # Add extra condition BEFORE random/limit
    if extra_conditions:
        query += " AND " + extra_conditions

    # Randomize & limit if needed
    query += " ORDER BY RANDOM()"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    return query, params


def get_random_card_with_cost(selected_sets, selected_types, cost, excluded_ids=None):
    # Build numeric cost filter as extra condition
    extra = f"CAST(REPLACE(c.cost, '$', '') AS INTEGER) = {cost}"
    query, params = build_query(
        selected_sets,
        selected_types,
        excluded_ids=excluded_ids,
        limit=1,
        extra_conditions=extra,
        excluded_types=excluded_types,
        excluded_card_names=excluded_card_names
    )

    return pd.read_sql_query(query, conn, params=params)




# -------------------------
# Function: generate new kingdom
# -------------------------
def generate_kingdom(selected_sets, selected_types, num_cards):
    kingdom_cards = pd.DataFrame()

    # 1. Pick one card with cost 2
    card2 = get_random_card_with_cost(selected_sets, selected_types, 2)
    if not card2.empty:
        kingdom_cards = pd.concat([kingdom_cards, card2], ignore_index=True)
    else:
        st.warning("No card with cost 2 found in the selected filters.")

    # 2. Pick one card with cost 3
    excluded_ids = kingdom_cards["id"].tolist() if not kingdom_cards.empty else None
    card3 = get_random_card_with_cost(selected_sets, selected_types, 3, excluded_ids=excluded_ids)
    if not card3.empty:
        kingdom_cards = pd.concat([kingdom_cards, card3], ignore_index=True)
    else:
        st.warning("No card with cost 3 found in the selected filters.")

    # 3. Fill remaining slots
    remaining = num_cards - len(kingdom_cards)
    if remaining > 0:
        excluded_ids = kingdom_cards["id"].tolist() if not kingdom_cards.empty else None
        query, params = build_query(
            selected_sets,
            selected_types,
            excluded_ids=excluded_ids,
            limit=remaining,
            excluded_types=excluded_types,
            excluded_card_names=excluded_card_names
        )
        remaining_cards = pd.read_sql_query(query, conn, params=params)
        kingdom_cards = pd.concat([kingdom_cards, remaining_cards], ignore_index=True)

    return kingdom_cards


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
        limit=1,
        excluded_types=excluded_types,
        excluded_card_names=excluded_card_names
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
