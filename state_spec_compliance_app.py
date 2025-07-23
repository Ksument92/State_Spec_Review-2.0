import streamlit as st
import pandas as pd
import re

st.title("State Spec Compliance Checker")

# Upload files
order_file = st.file_uploader("Upload Order Spreadsheet", type=["xlsx"])
state_spec_file = st.file_uploader("Upload State Spec Spreadsheet", type=["xlsx"])

def wildcard_to_regex(pattern):
    pattern = pattern.replace(".", r"\.")
    pattern = pattern.replace("XXX", r"\d{3}")
    pattern = pattern.replace("xx", r"\d{2}")
    pattern = pattern.replace("x", r"\d")
    pattern = pattern.replace("0x", r"0\d")
    pattern = pattern.replace(" ", "")
    return f"^{pattern}$"

def check_match(pattern, codes):
    try:
        regex = re.compile(wildcard_to_regex(str(pattern)))
        return any(regex.match(code) for code in codes)
    except re.error:
        return False

if order_file and state_spec_file:
    # Load order spreadsheet
    order_df = pd.read_excel(order_file, sheet_name="Mapics")
    ordered_codes = order_df["Item Numbers"].dropna().astype(str).str.strip().tolist()

    # Get available sheet names
    state_xl = pd.ExcelFile(state_spec_file)
    state_tabs = [sheet for sheet in state_xl.sheet_names if sheet not in ["OVERVIEW", "TEMPLATE", "STATE OWNERS", "DEALERS CBC", "DEALERS MG", "FMVSS", "ADA"]]

    # Select state sheet
    selected_state = st.selectbox("Select State", state_tabs)

    if selected_state:
        # Load selected state sheet and preview first 20 rows
        raw_df = pd.read_excel(state_spec_file, sheet_name=selected_state, skiprows=9)
        raw_df.dropna(axis=0, how='all', inplace=True)
        raw_df.dropna(axis=1, how='all', inplace=True)

        # Display available vehicle type columns
        available_columns = raw_df.columns.tolist()
        selected_vehicle_type = st.selectbox("Select Vehicle Type Column", available_columns)

        if selected_vehicle_type:
            # Clean and rename columns safely
            raw_df.columns = [str(c).strip() for c in raw_df.columns]

            # Try to locate the option code column
            option_col = None
            for col in raw_df.columns:
                if str(col).lower().startswith("option"):
                    option_col = col
                    break

            if option_col is None:
                st.error("Could not find a column labeled as 'Option'. Please check the spreadsheet format.")
            else:
                # Filter only rows where selected vehicle type column is non-empty
                valid_rows = raw_df[raw_df[selected_vehicle_type].notna() & raw_df[option_col].notna()]

                required_patterns = valid_rows[option_col].astype(str).str.strip()

                # Run comparison
                results = []
                for _, row in valid_rows.iterrows():
                    pattern = row[option_col]
                    matched = check_match(pattern, ordered_codes)
                    results.append({
                        "Pattern": pattern,
                        "Match Status": "✅ Matched" if matched else "❌ Missing",
                        "Feature": row.get("Feature", ""),
                        "Description": row.get("Source", "")
                    })

                result_df = pd.DataFrame(results)

                st.success("Compliance check complete.")
                st.dataframe(result_df)

                st.download_button(
                    label="Download Updated Compliance Summary",
                    data=result_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"Updated_{selected_state}_{selected_vehicle_type}_Compliance_Summary.csv",
                    mime="text/csv"
                )
