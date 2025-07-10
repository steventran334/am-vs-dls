import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

st.title("Archimedes vs DLS Data Comparison App")

# --- ARCHIMEDES DATA UPLOAD ---
st.header("Step 1: Upload Archimedes Files (label each population)")
arch_file1 = st.file_uploader("Upload first Archimedes CSV", type=["csv"], key="arch1")
arch_timepoint1 = st.text_input("Enter Archimedes time point for first file (e.g., 60 min):", key="arch_tp1")
arch_label1 = st.radio("First file: Select particle population", 
    ["Positively Buoyant Particles", "Negatively Buoyant Particles"], key="label1")

arch_file2 = st.file_uploader("Upload second Archimedes CSV (optional)", type=["csv"], key="arch2")
arch_timepoint2 = st.text_input("Enter Archimedes time point for second file (e.g., 60 min):", key="arch_tp2")
arch_label2 = st.radio("Second file: Select particle population", 
    ["Positively Buoyant Particles", "Negatively Buoyant Particles"], key="label2")

# Enforce unique choice per file
if arch_label1 == arch_label2 and arch_file2 is not None:
    st.warning("You cannot assign the same population label to both files. Please pick one Positively and one Negatively Buoyant.")
    st.stop()

# --- DLS DATA OPTIONS ---
st.header("Step 2: DLS Data Settings & Upload")
dls_type = st.radio("Select DLS type:", ["Back scatter", "MADLS"], key="dls_type")
dls_weight = st.radio("Select DLS weighting:", ["Intensity-weighted", "Volume-weighted", "Number-weighted"], key="dls_weight")
dls_file = st.file_uploader("Upload DLS Excel", type=["xlsx"], key="dls")

dls_timepoint = None
dls_timepoint_col = None

if dls_file is not None:
    dls_df_preview = pd.read_excel(dls_file, header=1)
    dls_timepoint_options = [col for col in dls_df_preview.columns if col.lower() != "diameter (nm)"]
    dls_timepoint = st.selectbox("Select DLS time point:", dls_timepoint_options)
    dls_timepoint_col = dls_timepoint

def process_arch_file(arch_file, arch_timepoint, arch_label):
    if arch_file is None or not arch_timepoint or not arch_label:
        return None, None, None, None
    arch_df = pd.read_csv(arch_file, skiprows=60)
    arch_df = arch_df[pd.to_numeric(arch_df["Bin Center"], errors="coerce").notna()]
    arch_df = arch_df[["Bin Center", "Average"]].copy()
    arch_df["Bin Center (nm)"] = pd.to_numeric(arch_df["Bin Center"], errors='coerce') * 1000
    arch_df = arch_df[["Bin Center (nm)", "Average"]].reset_index(drop=True)
    label = f"AM - {arch_label} (normalized)"
    arch_df.columns = ["Archimedes Bin Center (nm)", label]
    return arch_df["Archimedes Bin Center (nm)"].values, arch_df[label].values, arch_df, label

arch_curves = []
for arch_file, arch_timepoint, arch_label in [
        (arch_file1, arch_timepoint1, arch_label1), 
        (arch_file2, arch_timepoint2, arch_label2)]:
    arch_bin_nm, arch_conc, arch_df, arch_curve_label = process_arch_file(arch_file, arch_timepoint, arch_label)
    if arch_bin_nm is not None and arch_conc is not None and arch_df is not None:
        arch_curves.append({
            "bins": arch_bin_nm,
            "conc": arch_conc,
            "label": arch_curve_label,
        })

# --- PROCESS & VISUALIZE ---
if dls_file is not None and dls_timepoint and len(arch_curves) > 0:
    dls_df = pd.read_excel(dls_file, header=1)
    dls_df = dls_df[["Diameter (nm)", dls_timepoint_col]].copy()
    dls_df.columns = ["DLS Diameter (nm)", f"DLS {dls_timepoint}"]
    dls_diam_nm = dls_df["DLS Diameter (nm)"].dropna().values
    dls_intensity = dls_df[f"DLS {dls_timepoint}"].dropna().values

    # Use union of all arch bin centers for x-axis
    all_bins = np.unique(np.concatenate([curve["bins"] for curve in arch_curves]))
    df_out = pd.DataFrame({"Archimedes Bin Center (nm)": all_bins})

    # Interpolate & normalize each population
    def get_color(label):
        if "positively" in label.lower():
            return "blue"
        elif "negatively" in label.lower():
            return "black"
        else:
            return "gray"

    for curve in arch_curves:
        interp = np.interp(all_bins, curve["bins"], curve["conc"], left=np.nan, right=np.nan)
        interp_norm = interp / np.nanmax(interp) if np.nanmax(interp) > 0 else interp
        df_out[curve["label"]] = interp_norm  # <--- Just use the label, no duplicate (normalized)

    # Interpolate DLS to same bins
    interp_dls = np.interp(all_bins, dls_diam_nm, dls_intensity, left=np.nan, right=np.nan)
    interp_dls_norm = interp_dls / np.nanmax(interp_dls) if np.nanmax(interp_dls) > 0 else interp_dls

    dls_series_label = f"DLS {dls_type} {dls_weight} (interpolated, normalized)"
    df_out[dls_series_label] = interp_dls_norm

    # --- GRAPH SECTION ---
    st.header("Step 3: Visualization")
    user_title = st.text_input("Enter graph title:", "Archimedes vs DLS Comparison")
    fig, ax = plt.subplots(figsize=(8, 5))

    for curve in arch_curves:
        colname = curve["label"]
        ax.plot(df_out["Archimedes Bin Center (nm)"], df_out[colname],
                '-o', color=get_color(curve["label"]), label=curve["label"])

    ax.plot(df_out["Archimedes Bin Center (nm)"], 
            df_out[dls_series_label],
            '-s', color='red', label=dls_series_label)
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
    st.info("Upload at least one Archimedes file (with label and time point) and a DLS file to process and visualize your data.")
