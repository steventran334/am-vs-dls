import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Archimedes POS/NEG vs DLS Comparison")

# --- AM POS Upload ---
am_pos_files = st.file_uploader(
    "Upload Archimedes POS CSV files", type="csv", accept_multiple_files=True, key="pos")
am_pos_selected = None
if am_pos_files:
    am_pos_file_names = [f.name for f in am_pos_files]
    am_pos_selected = st.selectbox("Select POS data file", am_pos_file_names, key="pos_select")
    am_pos_idx = am_pos_file_names.index(am_pos_selected)
    am_pos_file = am_pos_files[am_pos_idx]
    df_pos = pd.read_csv(am_pos_file, skiprows=60)
    df_pos = df_pos[pd.to_numeric(df_pos["Bin Center"], errors="coerce").notna()]
    pos_bin_nm = df_pos["Bin Center"].astype(float).values * 1000  # µm to nm
    col_idx_pos = list(df_pos.columns).index("Bin Center")
    conc_col_pos = df_pos.columns[col_idx_pos + 1]
    pos_conc = df_pos[conc_col_pos].astype(float).values
    pos_norm_max = pos_conc / np.max(pos_conc) if np.max(pos_conc) != 0 else pos_conc
else:
    pos_bin_nm = pos_conc = pos_norm_max = None

# --- AM NEG Upload ---
am_neg_files = st.file_uploader(
    "Upload Archimedes NEG CSV files", type="csv", accept_multiple_files=True, key="neg")
am_neg_selected = None
if am_neg_files:
    am_neg_file_names = [f.name for f in am_neg_files]
    am_neg_selected = st.selectbox("Select NEG data file", am_neg_file_names, key="neg_select")
    am_neg_idx = am_neg_file_names.index(am_neg_selected)
    am_neg_file = am_neg_files[am_neg_idx]
    df_neg = pd.read_csv(am_neg_file, skiprows=60)
    df_neg = df_neg[pd.to_numeric(df_neg["Bin Center"], errors="coerce").notna()]
    neg_bin_nm = df_neg["Bin Center"].astype(float).values * 1000  # µm to nm
    col_idx_neg = list(df_neg.columns).index("Bin Center")
    conc_col_neg = df_neg.columns[col_idx_neg + 1]
    neg_conc = df_neg[conc_col_neg].astype(float).values
    neg_norm_max = neg_conc / np.max(neg_conc) if np.max(neg_conc) != 0 else neg_conc
else:
    neg_bin_nm = neg_conc = neg_norm_max = None

# --- DLS upload and dropdown ---
dls_file = st.file_uploader("Upload DLS Excel file", type=["xlsx"])
sheet_selected = None
if dls_file and pos_bin_nm is not None and neg_bin_nm is not None:
    xls = pd.ExcelFile(dls_file)
    sheets = xls.sheet_names
    sheet_selected = st.selectbox("Select DLS condition (sheet)", sheets)
    dls = pd.read_excel(xls, sheet_name=sheet_selected, header=[0,1,2], skiprows=[0,1])
    # Helper to find columns
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
        interp_pos = np.interp(pos_bin_nm, x, y, left=0, right=0)
        interp_neg = np.interp(neg_bin_nm, x, y, left=0, right=0)
        interp_pos_norm = interp_pos / np.max(interp_pos) if np.max(interp_pos) > 0 else interp_pos
        # Lines: DLS = black dotted, POS = blue, NEG = red
        ax.plot(pos_bin_nm, pos_norm_max, label="AM POS", color='blue', lw=2)
        ax.plot(neg_bin_nm, neg_norm_max, label="AM NEG", color='red', lw=2)
        ax.plot(pos_bin_nm, interp_pos_norm, label="DLS", color='black', lw=2, linestyle=":")
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
    st.warning("Upload Archimedes POS & NEG files and a DLS Excel file to generate plots.")

