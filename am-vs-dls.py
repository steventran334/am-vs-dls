import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Archimedes vs DLS Comparison")

# --- AM upload and dropdown ---
am_files = st.file_uploader("Upload Archimedes CSV files", type="csv", accept_multiple_files=True)
am_file_selected = None
am_df = None
am_x_pos_nm = am_x_neg_nm = am_y_pos = am_y_neg = None
am_y_pos_norm_max = am_y_neg_norm_max = None
am_conc_col_pos = am_conc_col_neg = None

if am_files:
    am_file_names = [f.name for f in am_files]
    am_file_selected = st.selectbox("Select Archimedes data file", am_file_names)
    am_file_idx = am_file_names.index(am_file_selected)
    am_file = am_files[am_file_idx]
    # Read file and extract POS and NEG (assume user uploads both POS and NEG, can clarify with labels if needed)
    df = pd.read_csv(am_file, skiprows=60)
    df = df[pd.to_numeric(df["Bin Center"], errors="coerce").notna()]
    bin_nm = df["Bin Center"].astype(float).values * 1000  # µm to nm
    col_idx = list(df.columns).index("Bin Center")
    conc_col = df.columns[col_idx + 1]
    conc = df[conc_col].astype(float).values
    norm_max = conc / np.max(conc) if np.max(conc) != 0 else conc
    am_x_nm, am_y, am_y_norm_max, am_conc_col = bin_nm, conc, norm_max, conc_col
else:
    st.warning("Upload Archimedes files to begin.")

# --- DLS upload and dropdown ---
dls_file = st.file_uploader("Upload DLS Excel file", type=["xlsx"])
sheet_selected = None
if dls_file:
    xls = pd.ExcelFile(dls_file)
    sheets = xls.sheet_names
    sheet_selected = st.selectbox("Select DLS condition (sheet)", sheets)
    dls = pd.read_excel(xls, sheet_name=sheet_selected, header=[0,1,2], skiprows=[0,1])
    # Prepare DLS data for all types
    def find_col(dls, type_main, weight):
        for col in dls.columns:
            col_str = ' '.join(str(c).lower() for c in col)
            if type_main in col_str and weight in col_str:
                return col
        return None
    dls_types = [
        ("back", "intensity"),
        ("back", "number"),
        ("back", "volume"),
        ("madls", "intensity"),
        ("madls", "number"),
        ("madls", "volume"),
    ]
    plot_titles = [
        "Back Scatter - Intensity",
        "Back Scatter - Number",
        "Back Scatter - Volume",
        "MADLS - Intensity",
        "MADLS - Number",
        "MADLS - Volume",
    ]
    fig, axs = plt.subplots(2, 3, figsize=(18, 8), sharex=True, sharey=True)
    for idx, ((main, weight), title) in enumerate(zip(dls_types, plot_titles)):
        ax = axs[idx // 3, idx % 3]
        size_col = find_col(dls, main, "size")
        dist_col = find_col(dls, main, weight)
        x = dls[size_col].astype(float).values
        y = dls[dist_col].astype(float).values
        msk = ~np.isnan(x) & ~np.isnan(y)
        x, y = x[msk], y[msk]
        interp = np.interp(am_x_nm, x, y, left=0, right=0)
        interp_norm = interp / np.max(interp) if np.max(interp) > 0 else interp
        ax.plot(am_x_nm, am_y_norm_max, label="AM (normalized by max)", color='blue', lw=2)
        ax.plot(am_x_nm, interp_norm, label="DLS", color='black', lw=2, linestyle=":")
        ax.set_xlim([0, 1000])
        ax.set_ylim([0, 1.1])
        ax.set_xticks([0, 200, 400, 600, 800, 1000])
        ax.set_xticklabels(['0', '200', '400', '600', '800', '1000'])
        ax.set_xlabel("Diameter (nm)")
        ax.set_title(title, fontsize=17, pad=16)
        if idx == 0:
            ax.legend()
        if idx % 3 == 0:
            ax.set_ylabel("Normalized Value (by max)")
    fig.suptitle(sheet_selected, fontsize=28)
    plt.tight_layout(rect=[0,0,1,0.95])
    st.pyplot(fig)
else:
    st.warning("Upload a DLS Excel file to generate plots.")
