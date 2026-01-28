import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile

st.title("Archimedes POS/NEG vs DLS Comparison")

st.markdown("""
<div style="background-color:#E8F0FE;padding:16px 24px 16px 24px;border-radius:14px;margin-bottom:20px;">
<b>Instructions:</b><br>
Archimedes graphs can be dropped in straight from Archimedes software.<br><br>
<b>DLS graphs must be formatted exactly:</b>
<ul style="margin-top:0;margin-bottom:0;">
<li>Sheet name: name of experiment (e.g. stock of NBs)</li>
<li>Back scatter data: in columns starting at column A</li>
<li>MADLS data: in columns starting at column H</li>
<li>Each contains intensity, number, and volume weighted distributions</li>
</ul>
Drop your files below.
</div>
""", unsafe_allow_html=True)

# --- CALLBACKS FOR SYNCING ---
def update_neg_from_pos():
    pass 

# --- FILE UPLOADS ---
am_pos_files = st.file_uploader(
    "Upload Archimedes POS CSV files", type="csv", accept_multiple_files=True, key="pos")
am_neg_files = st.file_uploader(
    "Upload Archimedes NEG CSV files", type="csv", accept_multiple_files=True, key="neg")

# Prepare sorted lists and maps
pos_map = {}
pos_names = []
if am_pos_files:
    pos_map = {f.name: f for f in am_pos_files}
    pos_names = sorted(list(pos_map.keys()))

neg_map = {}
neg_names = []
if am_neg_files:
    neg_map = {f.name: f for f in am_neg_files}
    neg_names = sorted(list(neg_map.keys()))

# --- SYNC LOGIC DEFINITION ---
def sync_neg():
    if "pos_select" in st.session_state and neg_names:
        current_pos = st.session_state.pos_select
        try:
            idx = pos_names.index(current_pos)
            if idx < len(neg_names):
                st.session_state.neg_select = neg_names[idx]
        except ValueError:
            pass

def sync_pos():
    if "neg_select" in st.session_state and pos_names:
        current_neg = st.session_state.neg_select
        try:
            idx = neg_names.index(current_neg)
            if idx < len(pos_names):
                st.session_state.pos_select = pos_names[idx]
        except ValueError:
            pass

# --- DROPDOWNS ---
col1, col2 = st.columns(2)

am_pos_selected = None
df_pos = None
pos_bin_nm = pos_conc = pos_norm_max = conc_col_pos = None

with col1:
    if pos_names:
        am_pos_selected = st.selectbox(
            "Select POS data file", 
            pos_names, 
            key="pos_select", 
            on_change=sync_neg 
        )
        am_pos_file = pos_map[am_pos_selected]
        am_pos_file.seek(0)
        df_pos = pd.read_csv(am_pos_file, skiprows=60)
        df_pos = df_pos[pd.to_numeric(df_pos["Bin Center"], errors="coerce").notna()]
        pos_bin_nm = df_pos["Bin Center"].astype(float).values * 1000 
        col_idx_pos = list(df_pos.columns).index("Bin Center")
        conc_col_pos = df_pos.columns[col_idx_pos + 1]
        pos_conc = df_pos[conc_col_pos].astype(float).values
        pos_norm_max = pos_conc / np.max(pos_conc) if np.max(pos_conc) != 0 else pos_conc

am_neg_selected = None
df_neg = None
neg_bin_nm = neg_conc = neg_norm_max = conc_col_neg = None

with col2:
    if neg_names:
        am_neg_selected = st.selectbox(
            "Select NEG data file", 
            neg_names, 
            key="neg_select", 
            on_change=sync_pos 
        )
        am_neg_file = neg_map[am_neg_selected]
        am_neg_file.seek(0)
        df_neg = pd.read_csv(am_neg_file, skiprows=60)
        df_neg = df_neg[pd.to_numeric(df_neg["Bin Center"], errors="coerce").notna()]
        neg_bin_nm = df_neg["Bin Center"].astype(float).values * 1000 
        col_idx_neg = list(df_neg.columns).index("Bin Center")
        conc_col_neg = df_neg.columns[col_idx_neg + 1]
        neg_conc = df_neg[conc_col_neg].astype(float).values
        neg_norm_max = neg_conc / np.max(neg_conc) if np.max(neg_conc) != 0 else neg_conc

# --- DLS upload and dropdown ---
dls_file = st.file_uploader("Upload DLS Excel file", type=["xlsx"])
sheet_selected = None

if (
    dls_file
    and pos_bin_nm is not None and neg_bin_nm is not None
    and conc_col_pos is not None and conc_col_neg is not None
):
    xls = pd.ExcelFile(dls_file)
    sheets = xls.sheet_names
    sheet_selected = st.selectbox("Select DLS condition (sheet)", sheets)
    dls = pd.read_excel(xls, sheet_name=sheet_selected, header=[0,1,2], skiprows=[0,1])

    # --- CUSTOM TITLE INPUT ---
    custom_title = st.text_input("Enter a custom title for the graph:", value=f"{sheet_selected}")
    
    # --- X-AXIS SLIDER ---
    x_axis_limit = st.slider("Adjust Max X-Axis Limit (nm)", min_value=500, max_value=10000, value=1000, step=100)

    def find_col(dls, type_main, weight):
        for col in dls.columns:
            col_str = ' '.join(str(c).lower() for c in col)
            if type_main in col_str and weight in col_str:
                return col
        return None

    # --- Plotting and Export Helper ---
    def get_plot_and_csvs(main_types, title_prefix):
        plot_titles = [
            f"{title_prefix} - Intensity",
            f"{title_prefix} - Number",
            f"{title_prefix} - Volume",
        ]
        weights = ["intensity", "number", "volume"]
        figs = []
        csv_files = []
        for i, (main, weight, title) in enumerate(zip(main_types, weights, plot_titles)):
            size_col = find_col(dls, main, "size")
            dist_col = find_col(dls, main, weight)
            if size_col is None or dist_col is None:
                continue
            
            # RAW DLS DATA (Correct for Plotting)
            x = dls[size_col].astype(float).values
            y = dls[dist_col].astype(float).values
            msk = ~np.isnan(x) & ~np.isnan(y)
            x, y = x[msk], y[msk]
            
            # INTERPOLATED DLS DATA (Correct for CSV Comparison)
            interp_pos = np.interp(pos_bin_nm, x, y, left=0, right=0)
            interp_pos_norm = interp_pos / np.max(interp_pos) if np.max(interp_pos) > 0 else interp_pos

            # Pad for CSV output
            n_rows = max(len(pos_bin_nm), len(x))
            pad = lambda arr, l: np.pad(arr, (0, l - len(arr)), constant_values=np.nan)
            df_csv = pd.DataFrame({
                "Archimedes Diameter (nm)": pad(pos_bin_nm, n_rows),
                f"{conc_col_pos} (particles/mL)": pad(pos_conc, n_rows),
                f"{conc_col_pos} (normalized by max)": pad(pos_norm_max, n_rows),
                "DLS Diameter (nm)": pad(x, n_rows),
                "DLS Intensity (%)": pad(y, n_rows),
                "DLS (interpolated to AM)": pad(interp_pos, n_rows),
                "DLS (interpolated, normalized by max)": pad(interp_pos_norm, n_rows)
            })

            # Plot - Individual (hidden)
            fig, ax = plt.subplots(figsize=(5,4))
            ax.plot(pos_bin_nm, pos_norm_max, label="AM POS", color='blue', lw=2)
            ax.plot(neg_bin_nm, neg_norm_max, label="AM NEG", color='red', lw=2)
            
            # Plot RAW DLS data
            y_norm_plot = y / np.max(y) if np.max(y) > 0 else y
            ax.plot(x, y_norm_plot, label="DLS", color='black', lw=2, linestyle=":")
            
            # Apply User-Selected Limit
            ax.set_xlim(left=0, right=x_axis_limit)
            
            ax.set_xlabel("Diameter (nm)")
            ax.set_ylabel("Normalized Value (by max)")
            ax.set_title(title)
            ax.legend()
            figs.append(fig)

            # Save CSV
            csv_data = df_csv.to_csv(index=False)
            fname_base = f"{sheet_selected}_{title.replace(' ','_')}"
            csv_files.append((f"{fname_base}.csv", csv_data))
            plt.close(fig)
        return figs, csv_files

    # --- ZIP Helper ---
    def make_zip(name_pairs):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for fname, data in name_pairs:
                zf.writestr(fname, data)
        return zip_buffer.getvalue()

    # --- BACK SCATTER PREVIEW & DOWNLOAD ---
    st.subheader("Back Scatter Distributions")
    back_figs, back_csv_files = get_plot_and_csvs(["back"]*3, "Back Scatter")
    if back_figs:
        fig, axs = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        fig.suptitle(custom_title, fontsize=20)

        for i, f in enumerate(back_figs):
            ax = axs[i]
            tmp = f.axes[0]
            for line in tmp.lines:
                ax.plot(line.get_xdata(), line.get_ydata(),
                        label=line.get_label(), color=line.get_color(),
                        lw=line.get_linewidth(), linestyle=line.get_linestyle())
            
            # Apply Limit to Preview
            ax.set_xlim(0, x_axis_limit)
            ax.set_ylim(tmp.get_ylim())

            # --- MOVED X-AXIS TO Y=0 ---
            ax.spines['bottom'].set_position(('data', 0))
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            # ---------------------------

            ax.set_xlabel(tmp.get_xlabel())
            ax.set_title(tmp.get_title())
            if i == 0:
                ax.set_ylabel(tmp.get_ylabel())
            ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        
        svg_buf = io.StringIO()
        fig.savefig(svg_buf, format="svg", bbox_inches='tight')
        st.download_button(
            label="Download Back Scatter (1x3 SVG)",
            data=svg_buf.getvalue(),
            file_name=f"{sheet_selected}_BackScatter_1x3.svg",
            mime="image/svg+xml"
        )
        plt.close(fig)
        st.download_button(
            label="Download All Back Scatter CSVs (ZIP)",
            data=make_zip(back_csv_files),
            file_name=f"{sheet_selected}_BackScatter_CSVs.zip",
            mime="application/zip"
        )

    # --- MADLS PREVIEW & DOWNLOAD ---
    st.subheader("MADLS Distributions")
    madls_figs, madls_csv_files = get_plot_and_csvs(["madls"]*3, "MADLS")
    if madls_figs:
        fig, axs = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        fig.suptitle(custom_title, fontsize=20)
        
        for i, f in enumerate(madls_figs):
            ax = axs[i]
            tmp = f.axes[0]
            for line in tmp.lines:
                ax.plot(line.get_xdata(), line.get_ydata(),
                        label=line.get_label(), color=line.get_color(),
                        lw=line.get_linewidth(), linestyle=line.get_linestyle())
            
            # Apply Limit to Preview
            ax.set_xlim(0, x_axis_limit)
            ax.set_ylim(tmp.get_ylim())

            # --- MOVED X-AXIS TO Y=0 ---
            ax.spines['bottom'].set_position(('data', 0))
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            # ---------------------------

            ax.set_xlabel(tmp.get_xlabel())
            ax.set_title(tmp.get_title())
            if i == 0:
                ax.set_ylabel(tmp.get_ylabel())
            ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        
        svg_buf = io.StringIO()
        fig.savefig(svg_buf, format="svg", bbox_inches='tight')
        st.download_button(
            label="Download MADLS (1x3 SVG)",
            data=svg_buf.getvalue(),
            file_name=f"{sheet_selected}_MADLS_1x3.svg",
            mime="image/svg+xml"
        )
        plt.close(fig)
        st.download_button(
            label="Download All MADLS CSVs (ZIP)",
            data=make_zip(madls_csv_files),
            file_name=f"{sheet_selected}_MADLS_CSVs.zip",
            mime="application/zip"
        )

else:
    st.info("Upload POS & NEG Archimedes files, select both, and upload/select a DLS Excel file and condition (sheet) to view plots and downloads.")
