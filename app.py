
import streamlit as st
import pandas as pd
from io import BytesIO

# === Helper Functions ===
def auto_detect_column(columns, keywords):
    for kw in keywords:
        for col in columns:
            if isinstance(col, str) and kw.lower() in col.lower():
                return col
    return None

def normalize_name(name):
    if pd.isna(name):
        return ""
    return str(name).lower().strip()

def partial_match(n1, n2):
    return bool(set(n1.split()) & set(n2.split()))

# === Streamlit UI ===
st.title("Driver Hire Date Filler Tool")

st.markdown("Upload two Excel files to match driver names and fill hire dates.")

file1 = st.file_uploader("Upload File 1 (Source Data)", type=["xlsx"])
skip1 = st.number_input("Skip how many rows in File 1?", min_value=0, value=0, step=1)

file2 = st.file_uploader("Upload File 2 (To Fill Dates)", type=["xlsx"])
skip2 = st.number_input("Skip how many rows in File 2?", min_value=0, value=0, step=1)

if file1 and file2:
    # Load Excel
    df1_raw = pd.read_excel(file1, skiprows=skip1)
    xl2 = pd.ExcelFile(file2)
    st.write("Available sheets in File 2:", xl2.sheet_names)
    sheet2 = st.selectbox("Select sheet to edit in File 2", xl2.sheet_names)
    df2_raw = pd.read_excel(file2, sheet_name=sheet2, skiprows=skip2)

    df1 = df1_raw.copy()
    df2_edit = df2_raw.copy()

    # Auto-detect columns
    name_col1 = auto_detect_column(df1.columns, ["Driver Name", "Driver Full Name", "Driver Last Name", "Name"])
    date_col1 = auto_detect_column(df1.columns, ["Date of Hire", "Hire Date", "DOH"])
    cdl_col1 = auto_detect_column(df1.columns, ["CDL", "CDL Number", "CDL No", "DL No"])

    name_col2 = auto_detect_column(df2_edit.columns, ["Driver Name", "Driver Full Name", "Name of Driver"])
    date_col2 = auto_detect_column(df2_edit.columns, ["Date of Hire", "Hire Date", "DOH"])
    cdl_col2 = auto_detect_column(df2_edit.columns, ["CDL", "CDL Number", "CDL No", "DL No"])

    # Ask user if needed
    if not name_col1: name_col1 = st.text_input("Enter Driver Name column in File 1:")
    if not date_col1: date_col1 = st.text_input("Enter Date of Hire column in File 1:")
    if not name_col2: name_col2 = st.text_input("Enter Driver Name column in File 2:")

    if not date_col2:
        date_col2 = "Date of Hire"
        df2_edit[date_col2] = pd.NaT

    if name_col1 and date_col1 and name_col2:
        df1['__name1'] = df1[name_col1].apply(normalize_name)
        df2_edit['__name2'] = df2_edit[name_col2].apply(normalize_name)

        df1[date_col1] = pd.to_datetime(df1[date_col1], errors='coerce')
        df2_edit[date_col2] = pd.to_datetime(df2_edit[date_col2], errors='coerce')

        for idx, row in df2_edit[df2_edit[date_col2].isna()].iterrows():
            name2 = row['__name2']
            matched = False
            for _, r1 in df1.iterrows():
                if partial_match(name2, r1['__name1']):
                    df2_edit.at[idx, date_col2] = r1[date_col1]
                    matched = True
                    break
            if not matched and cdl_col1 and cdl_col2:
                cdl_val = row.get(cdl_col2)
                if pd.notna(cdl_val):
                    match = df1[df1[cdl_col1] == cdl_val]
                    if not match.empty:
                        df2_edit.at[idx, date_col2] = match.iloc[0][date_col1]

        df2_edit[date_col2] = pd.to_datetime(df2_edit[date_col2], errors='coerce').dt.strftime('%m/%d/%Y')

        # Combine skipped + edited data
        df2_final = pd.concat([df2_raw.iloc[:0], df2_edit], ignore_index=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for s in xl2.sheet_names:
                df = pd.read_excel(file2, sheet_name=s)
                if s == sheet2:
                    df2_final.to_excel(writer, sheet_name=s, index=False)
                else:
                    df.to_excel(writer, sheet_name=s, index=False)
        st.success("Processing complete. Download below.")
        st.download_button("Download Updated Excel", output.getvalue(), file_name="output.xlsx")
