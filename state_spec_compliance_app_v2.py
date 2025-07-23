import streamlit as st
import pandas as pd
import re

st.title("State Spec Compliance Checker")

# Upload files
order_file = st.file_uploader("Upload Order Spreadsheet", type=["xlsx"])
state_spec_file = st.file_uploader("Upload State Spec Spreadsheet", type=["xlsx", "xls", "xlsm"])

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
    try:
        order_df = pd.read_excel(order_file, sheet_name="Mapics")
    except Exception as e:
        st.error(f"Error loading order sheet: {e}")
        st.stop()

    ordered_codes = order_df["Item Numbers"].dropna().astype(str).str.strip().tolist()

    # Load state spec workbook and show tab list
    try:
        state_xl = pd.ExcelFile(state_spec_file)
    except Exception as e:
        st.error(f"Error reading state spec workbook: {e}")
        st.stop()

    state_tabs = [s for s in state_xl.sheet_names if s not in ["OVERVIEW", "TEMPLATE", "STATE OWNERS", "DEALERS CBC", "DEALERS MG", "FMVSS", "ADA"]]
    selected_state = st.selectbox("Select State", state_tabs)

    if selected_state:
        # Load selected tab and clean
        raw_df = pd.read_excel(state_spec_file, sheet_name=selected_state, skiprows=9)
        raw_df.dropna(axis=0, how='all', inplace=True)
        raw_df.dropna(axis=1, how='all', inplace=True)
        raw_df.columns = [str(c).strip() for c in raw_df.columns]

        # Identify potential vehicle type columns
        valid_columns = []
        for col in raw_df.columns:
            # Accept if column has >3 non-empty entries and not named 'Feature', 'Source', etc.
            if raw_df[col].notna().sum() >= 3 and not any(key in col.lower() for key in ["feature", "source", "rev", "description", "date"]):
                valid_columns.append(col)

        selected_vehicle_type = st.selectbox("Select Vehicle Type Column", valid_columns)

        # Try to locate the option code column
        option_col = next((c for c in raw_df.columns if "option" in c.lower()), None)

        if not option_col:
            st.error("Could not find an 'Option' column in the selected sheet.")
        elif selected_vehicle_type:
            # Filter MFSAB-required options
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
