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

# Dominion Kingdom Generator Web App
#
# This Streamlit app generates a random Dominion kingdom of cards.
# Each card name appears only once (including "Castle" cards).

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
excluded_types = ['Event', 'Curse', 'Landmark']
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
    excluded_names=None, 
    limit=None, 
    extra_conditions="", 
    excluded_types=None, 
    excluded_card_names=None
):
    if excluded_types is None:
        excluded_types = []
    if excluded_card_names is None:
        excluded_card_names = []
    if excluded_names is None:
        excluded_names = []

    query = """
    SELECT *
    FROM (
        SELECT DISTINCT
            c.id,
            CASE 
                WHEN c.name LIKE '%Castle%' THEN 'Castle'
                ELSE c.name
            END AS name,
            c.types,
            c.cost,
            cs.set_name,
            c.text
        FROM cards c
        JOIN card_sets cs ON c.id = cs.card_id
        JOIN card_types ct ON c.id = ct.card_id
    ) AS x
    WHERE 1=1
    """
    params = []

    # Filter expansions
    if selected_sets:
        query += " AND x.set_name IN ({})".format(",".join(["?"] * len(selected_sets)))
        params += selected_sets

    # Exclude types
    if excluded_types:
        query += """
        AND x.id NOT IN (
            SELECT card_id FROM card_types WHERE type IN ({} )
        )
        """.format(",".join(["?"] * len(excluded_types)))
        params += excluded_types

    # Exclude fixed card names
    if excluded_card_names:
        query += " AND x.name NOT IN ({})".format(",".join(["?"] * len(excluded_card_names)))
        params += excluded_card_names

    # Exclude already-picked names
    if excluded_names:
        query += " AND x.name NOT IN ({})".format(",".join(["?"] * len(excluded_names)))
        params += excluded_names

    # Exclude IDs
    if excluded_ids:
        query += " AND x.id NOT IN ({})".format(",".join(["?"] * len(excluded_ids)))
        params += excluded_ids

    # Extra conditions (e.g., cost)
    if extra_conditions:
        query += " AND " + extra_conditions

    # Random + limit
    query += " ORDER BY RANDOM()"
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    return query, params

# -------------------------
# Function: get random card
# -------------------------
def get_random_card(selected_sets, selected_types, cost=None, excluded_ids=None, excluded_names=None):
    extra = ""
    if cost is not None:
        extra = f"CAST(REPLACE(x.cost, '$', '') AS INTEGER) = {cost}"
    query, params = build_query(
        selected_sets,
        selected_types,
        excluded_ids=excluded_ids,
        excluded_names=excluded_names,
        limit=1,
        extra_conditions=extra,
        excluded_types=excluded_types,
        excluded_card_names=excluded_card_names
    )
    return pd.read_sql_query(query, conn, params=params)

# -------------------------
# Function: generate kingdom
# -------------------------
def generate_kingdom(selected_sets, selected_types, num_cards):
    kingdom_cards = pd.DataFrame()
    picked_names = []

    # Pick one card with cost 2
    card2 = get_random_card(selected_sets, selected_types, cost=2, excluded_names=picked_names)
    if not card2.empty:
        kingdom_cards = pd.concat([kingdom_cards, card2], ignore_index=True)
        picked_names.extend(card2["name"].tolist())

    # Pick one card with cost 3
    card3 = get_random_card(selected_sets, selected_types, cost=3, excluded_ids=kingdom_cards["id"].tolist(), excluded_names=picked_names)
    if not card3.empty:
        kingdom_cards = pd.concat([kingdom_cards, card3], ignore_index=True)
        picked_names.extend(card3["name"].tolist())

    # Fill remaining slots
    remaining = num_cards - len(kingdom_cards)
    while remaining > 0:
        excluded_ids = kingdom_cards["id"].tolist()
        new_card = get_random_card(selected_sets, selected_types, excluded_ids=excluded_ids, excluded_names=picked_names)
        if new_card.empty:
            break
        kingdom_cards = pd.concat([kingdom_cards, new_card], ignore_index=True)
        picked_names.extend(new_card["name"].tolist())
        remaining = num_cards - len(kingdom_cards)

    return kingdom_cards

# -------------------------
# Function: reshuffle one card
# -------------------------
def reshuffle_card(idx):
    kingdom = st.session_state.kingdom
    filters = st.session_state.filters

    remaining_ids = kingdom.drop(idx)["id"].tolist()
    remaining_names = kingdom.drop(idx)["name"].tolist()

    replacement = get_random_card(
        filters["selected_sets"],
        filters["selected_types"],
        excluded_ids=remaining_ids,
        excluded_names=remaining_names
    )

    if not replacement.empty:
        kingdom.loc[idx] = replacement.iloc[0]
        st.session_state.kingdom = kingdom

# -------------------------
# Filters UI
# -------------------------
preselected_sets = ["Base", "Prosperity", "Plunder"]
selected_sets = st.multiselect("Choose expansions:", options=all_sets, default=preselected_sets)
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
    st.rerun()

# -------------------------
# Display Kingdom + Reshuffle Buttons
# -------------------------
if st.session_state.kingdom is not None:
    st.subheader("🎴 Generated Kingdom")
    df = st.session_state.kingdom

    st.data_editor(
        df[["name", "types", "set_name", "cost", "text"]],
        column_config={"text": st.column_config.TextColumn("Card Text", max_chars=1800)},
        hide_index=True,
        use_container_width=True
    )

    st.markdown("### Card List (click 🔄 to reshuffle one):")

    for idx, row in df.iterrows():
        col1, col2 = st.columns([0.15, 4])
        with col1:
            st.button("🔄", key=f"reshuffle_{idx}", help="Reshuffle this card")
        with col2:
            st.markdown(f"**{row['name']}** — *{row['set_name']}* ({row['types']})")
        if st.session_state.get(f"reshuffle_{idx}"):
            reshuffle_card(idx)
            st.rerun()

# Close DB
conn.close()

