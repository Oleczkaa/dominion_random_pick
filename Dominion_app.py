import sqlite3
import streamlit as st
import pandas as pd

# Connect to your Dominion database
DB = "dominion.db"
conn = sqlite3.connect(DB)

st.title("Dominion Kingdom Generator")

# Load available sets and types for the UI
df_sets = pd.read_sql_query("SELECT DISTINCT set_name FROM card_sets ORDER BY set_name", conn)
df_types = pd.read_sql_query("SELECT DISTINCT type FROM card_types ORDER BY type", conn)

all_sets = sorted(df_sets["set_name"].tolist())
all_types = sorted(df_types["type"].tolist())

# --- Streamlit UI ---
selected_sets = st.multiselect("Choose expansions:", all_sets)
selected_types = st.multiselect("Choose card types:", all_types)
num_cards = st.slider("How many cards do you want?", 1, 15, 10)

# Button to generate kingdom
if st.button("Generate Kingdom"):
    # SQL query to select matching cards
    query = """
    SELECT DISTINCT c.id, c.name, c.types, c.cost, cs.set_name
    FROM cards c
    JOIN card_sets cs ON c.id = cs.card_id
    JOIN card_types ct ON c.id = ct.card_id
    WHERE 1=1
    """
    params = []

    # Filter by selected sets
    if selected_sets:
        query += " AND cs.set_name IN ({})".format(",".join(["?"] * len(selected_sets)))
        params += selected_sets

    # Filter by selected types
    if selected_types:
        query += """
        AND c.id IN (
            SELECT card_id FROM card_types
            WHERE type IN ({})
        )
        """.format(",".join(["?"] * len(selected_types)))
        params += selected_types

    # Randomize and limit number of cards
    query += " ORDER BY RANDOM() LIMIT ?"
    params.append(num_cards)

    # Execute query
    results = pd.read_sql_query(query, conn, params=params)

    if results.empty:
        st.warning("No cards match your filters.")
    else:
        st.subheader("🎴 Generated Kingdom")
        # Display table
        st.dataframe(results[["name", "types", "set_name", "cost"]])
        
        # Pretty list output
        st.markdown("### Card List:")
        for _, row in results.iterrows():
            st.markdown(f"- **{row['name']}** — *{row['set_name']}* ({row['types']})")

# Close database connection when Streamlit stops
conn.close()
