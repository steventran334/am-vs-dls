import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

st.title("Archimedes vs DLS Data Comparison App")

# --- ARCHIMEDES DATA UPLOAD ---
st.header("Step 1: Upload Archimedes Data (.csv)")
arch_file = st.file_uploader("Upload Archimedes CSV", type=["csv"], key="arch")
arch_timepoint = st.text_input("Enter Archimedes time point (e.g., 60 min):", key="arch_tp")

# --- DLS DATA UPLOAD ---
st.header("Step 2: Upload DLS Data (.xlsx)")
dls_file = st.file_uploader("Upload DLS Excel", type=["xlsx"], key="dls")
dls_timepoint = None
dls_timepoint_col = None
dls_diam_col = None

if dls_file is not None:
    # Read the sheet using the first row as header
    dls_df_preview = pd.read_excel(dls_file, header=0)
    dls_columns = dls_df_preview.columns.tolist()
    # Use the first column as diameters (robust to header name)
    dls_diam_col = dls_columns[0]
    dls_timepoint_options = dls_columns[1:]
    dls_timepoint = st.selectbox("Select DLS time point column:", dls_timepoint_options)
    dls_timepoint_col = dls_timepoint

# --- DATA PROCESSING ---
if arch_file is not None and dls_file is not None and arch_timepoint and dls_timepoint:
    # Read and clean Archimedes
    arch_df = pd.read_csv(arch_file, skiprows=60)
    arch_df = arch_df[pd.to_numeric(arch_df["Bin Center"], errors="coerce").notna()]
    arch_df = arch_df[["Bin Center", "Average"]].copy()
    arch_df["Bin Center (nm)"] = pd.to_numeric(arch_df["Bin Center"], errors='coerce') * 1000
    arch_df = arch_df[["Bin Center (nm)", "Average"]].reset_index(drop=True)
    arch_df.columns = ["Archimedes Bin Center (nm)", f"Archimedes {arch_timepoint}"]

    # Read and extract DLS
    dls_df = pd.read_excel(dls_file, header=0)
    dls_df = dls_df[[dls_diam_col, dls_timepoint_col]].copy()
    dls_df.columns = ["DLS Diameter (nm)", f"DLS {dls_timepoint}"]

    # Interpolate DLS to Archimedes bins
    arch_bin_nm = arch_df["Archimedes Bin Center (nm)"].values
    arch_conc = arch_df[f"Archimedes {arch_timepoint}"].values
    dls_diam_nm = dls_df["DLS Diameter (nm)"].dropna().values
    dls_intensity = dls_df[f"DLS {dls_timepoint}"].dropna().values

    interp_dls = np.interp(
        arch_bin_nm,
        dls_diam_nm,
        dls_intensity,
        left=np.nan,
        right=np.nan
    )
    interp_dls_norm = interp_dls / np.nanmax(interp_dls) if np.nanmax(interp_dls) > 0 else interp_dls
    arch_conc_norm = arch_conc / np.nanmax(arch_conc) if np.nanmax(arch_conc) > 0 else arch_conc

    # Build output DataFrame
    df_out = pd.DataFrame({
        "Archimedes Bin Center (nm)": arch_bin_nm,
        f"Archimedes {arch_timepoint} (raw)": arch_conc,
        f"Archimedes {arch_timepoint} (normalized)": arch_conc_norm,
        "DLS Intensity (interpolated, raw)": interp_dls,
        "DLS Intensity (interpolated, normalized)": interp_dls_norm
    })

    # --- GRAPH SECTION ---
    st.header("Step 3: Visualization")
    user_title = st.text_input("Enter graph title:", "Archimedes vs DLS Comparison")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df_out["Archimedes Bin Center (nm)"], df_out[f"Archimedes {arch_timepoint} (normalized)"], '-o', color='blue', label="Archimedes Concentration (normalized)")
    ax.plot(df_out["Archimedes Bin Center (nm)"], df_out["DLS Intensity (interpolated, normalized)"], '-s', color='red', label="DLS Intensity (interpolated, normalized)")
    ax.set_xlabel("Diameter (nm)")
    ax.set_ylabel("Normalized value (a.u.)")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title(user_title)
    st.pyplot(fig)

    # Download SVG
    svg_buffer = io.StringIO()
    fig.savefig(svg_buffer, format="svg")
    st.download_button(
        label="Download plot as SVG",
        data=svg_buffer.getvalue(),
        file_name="arch_dls_plot.svg",
        mime="image/svg+xml"
    )

    # --- DATA OUTPUT SECTION ---
    st.header("Step 4: Output Data")
    st.dataframe(df_out.head(25))
    excel_buffer = io.BytesIO()
    df_out.to_excel(excel_buffer, index=False)
    st.download_button(
        label="Download processed table as Excel",
        data=excel_buffer.getvalue(),
        file_name="archimedes_dls_processed.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Upload both files and specify the time points to process and visualize your data.")

