import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

st.title("Archimedes vs DLS Data Comparison App")

# --- ARCHIMEDES 1 DATA UPLOAD ---
st.header("Step 1: Upload Archimedes Data (.csv) for Positively Buoyant Particles")
arch_file_pos = st.file_uploader("Upload Archimedes CSV (Positive)", type=["csv"], key="arch_pos")
arch_timepoint_pos = st.text_input("Enter Archimedes time point (e.g., 60 min) for Positively Buoyant Particles:", key="arch_tp_pos")
show_pos = st.checkbox("Show Positively Buoyant Particles", value=True)

# --- ARCHIMEDES 2 DATA UPLOAD ---
st.header("Step 2: Upload Archimedes Data (.csv) for Negatively Buoyant Particles")
arch_file_neg = st.file_uploader("Upload Archimedes CSV (Negative)", type=["csv"], key="arch_neg")
arch_timepoint_neg = st.text_input("Enter Archimedes time point (e.g., 60 min) for Negatively Buoyant Particles:", key="arch_tp_neg")
show_neg = st.checkbox("Show Negatively Buoyant Particles", value=False)

# --- DLS DATA UPLOAD ---
st.header("Step 3: Upload DLS Data (.xlsx)")
dls_file = st.file_uploader("Upload DLS Excel", type=["xlsx"], key="dls")
dls_timepoint = None
dls_timepoint_col = None
dls_diam_col = None

if dls_file is not None:
    dls_df_preview = pd.read_excel(dls_file, header=0)
    dls_columns = dls_df_preview.columns.tolist()
    dls_diam_col = dls_columns[0]
    dls_timepoint_options = dls_columns[1:]
    dls_timepoint = st.selectbox("Select DLS time point column:", dls_timepoint_options)
    dls_timepoint_col = dls_timepoint

def process_arch_file(arch_file, arch_timepoint):
    if arch_file is None or not arch_timepoint:
        return None, None, None
    arch_df = pd.read_csv(arch_file, skiprows=60)
    arch_df = arch_df[pd.to_numeric(arch_df["Bin Center"], errors="coerce").notna()]
    arch_df = arch_df[["Bin Center", "Average"]].copy()
    arch_df["Bin Center (nm)"] = pd.to_numeric(arch_df["Bin Center"], errors='coerce') * 1000
    arch_df = arch_df[["Bin Center (nm)", "Average"]].reset_index(drop=True)
    arch_df.columns = ["Archimedes Bin Center (nm)", f"Archimedes {arch_timepoint}"]
    return arch_df["Archimedes Bin Center (nm)"].values, arch_df[f"Archimedes {arch_timepoint}"].values, arch_df

if arch_file_pos is not None and arch_timepoint_pos and dls_file is not None and dls_timepoint:
    arch_bin_nm_pos, arch_conc_pos, arch_df_pos = process_arch_file(arch_file_pos, arch_timepoint_pos)
else:
    arch_bin_nm_pos, arch_conc_pos, arch_df_pos = None, None, None

if arch_file_neg is not None and arch_timepoint_neg and dls_file is not None and dls_timepoint:
    arch_bin_nm_neg, arch_conc_neg, arch_df_neg = process_arch_file(arch_file_neg, arch_timepoint_neg)
else:
    arch_bin_nm_neg, arch_conc_neg, arch_df_neg = None, None, None

if dls_file is not None and dls_timepoint and (arch_df_pos is not None or arch_df_neg is not None):
    dls_df = pd.read_excel(dls_file, header=0)
    dls_df = dls_df[[dls_diam_col, dls_timepoint_col]].copy()
    dls_df.columns = ["DLS Diameter (nm)", f"DLS {dls_timepoint}"]
    dls_diam_nm = dls_df["DLS Diameter (nm)"].dropna().values
    dls_intensity = dls_df[f"DLS {dls_timepoint}"].dropna().values

    # Use union of all arch bin centers to define the common interpolation grid
    bin_sets = []
    if show_pos and arch_bin_nm_pos is not None: bin_sets.append(set(arch_bin_nm_pos))
    if show_neg and arch_bin_nm_neg is not None: bin_sets.append(set(arch_bin_nm_neg))
    if not bin_sets:
        st.info("Check at least one Archimedes population to display.")
        st.stop()
    arch_bin_union = np.array(sorted(set().union(*bin_sets))) if bin_sets else None

    # Interpolate and normalize
    df_out = pd.DataFrame({"Archimedes Bin Center (nm)": arch_bin_union})
    # Positive
    if show_pos and arch_bin_nm_pos is not None:
        arch_conc_pos_interp = np.interp(arch_bin_union, arch_bin_nm_pos, arch_conc_pos, left=np.nan, right=np.nan)
        arch_conc_pos_norm = arch_conc_pos_interp / np.nanmax(arch_conc_pos_interp) if np.nanmax(arch_conc_pos_interp) > 0 else arch_conc_pos_interp
        df_out[f"Archimedes {arch_timepoint_pos} (Positively Buoyant, normalized)"] = arch_conc_pos_norm
    # Negative
    if show_neg and arch_bin_nm_neg is not None:
        arch_conc_neg_interp = np.interp(arch_bin_union, arch_bin_nm_neg, arch_conc_neg, left=np.nan, right=np.nan)
        arch_conc_neg_norm = arch_conc_neg_interp / np.nanmax(arch_conc_neg_interp) if np.nanmax(arch_conc_neg_interp) > 0 else arch_conc_neg_interp
        df_out[f"Archimedes {arch_timepoint_neg} (Negatively Buoyant, normalized)"] = arch_conc_neg_norm

    # Interpolate DLS to same bins
    interp_dls = np.interp(arch_bin_union, dls_diam_nm, dls_intensity, left=np.nan, right=np.nan)
    interp_dls_norm = interp_dls / np.nanmax(interp_dls) if np.nanmax(interp_dls) > 0 else interp_dls
    df_out["DLS Intensity (interpolated, normalized)"] = interp_dls_norm

    # --- GRAPH SECTION ---
    st.header("Step 4: Visualization")
    user_title = st.text_input("Enter graph title:", "Archimedes vs DLS Comparison")
    fig, ax = plt.subplots(figsize=(8, 5))

    if show_pos and arch_bin_nm_pos is not None:
        ax.plot(df_out["Archimedes Bin Center (nm)"], 
                df_out[f"Archimedes {arch_timepoint_pos} (Positively Buoyant, normalized)"],
                '-o', color='blue', label="Positively Buoyant Particles")
    if show_neg and arch_bin_nm_neg is not None:
        ax.plot(df_out["Archimedes Bin Center (nm)"], 
                df_out[f"Archimedes {arch_timepoint_neg} (Negatively Buoyant, normalized)"],
                '-^', color='green', label="Negatively Buoyant Particles")
    ax.plot(df_out["Archimedes Bin Center (nm)"], 
            df_out["DLS Intensity (interpolated, normalized)"],
            '-s', color='red', label="DLS Intensity (interpolated, normalized)")
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
    st.header("Step 5: Output Data")
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
