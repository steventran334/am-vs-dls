import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile

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
    pos_bin_nm = pos_conc = pos_norm_max = conc_col_pos = None

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
    neg_bin_nm = neg_conc = neg_norm_max = conc_col_neg = None

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
        svg_files = []
        csv_files = []
        for i, (main, weight, title) in enumerate(zip(main_types, weights, plot_titles)):
            size_col = find_col(dls, main, "size")
            dist_col = find_col(dls, main, weight)
            if size_col is None or dist_col is None:
                continue
            x = dls[size_col].astype(float).values
            y = dls[dist_col].astype(float).values
            msk = ~np.isnan(x) & ~np.isnan(y)
            x, y = x[msk], y[msk]
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

            # Plot
            fig, ax = plt.subplots(figsize=(5,4))
            ax.plot(pos_bin_nm, pos_norm_max, label="AM POS", color='blue', lw=2)
            ax.plot(neg_bin_nm, neg_norm_max, label="AM NEG", color='red', lw=2)
            ax.plot(pos_bin_nm, interp_pos_norm, label="DLS", color='black', lw=2, linestyle=":")
            ax.set_xlim([0, 1000])
            ax.set_ylim([0, 1.1])
            ax.set_xticks([0, 200, 400, 600, 800, 1000])
            ax.set_xticklabels(['0', '200', '400', '600', '800', '1000'])
            ax.set_xlabel("Diameter (nm)")
            ax.set_ylabel("Normalized Value (by max)")
            ax.set_title(title)
            ax.legend()
            figs.append(fig)

            # Save SVG and CSV in memory for zipping
            svg_buf = io.StringIO()
            fig.savefig(svg_buf, format="svg", bbox_inches='tight')
            svg_data = svg_buf.getvalue()
            fname_base = f"{sheet_selected}_{title.replace(' ','_')}"
            svg_files.append((f"{fname_base}.svg", svg_data))
            csv_data = df_csv.to_csv(index=False)
            csv_files.append((f"{fname_base}.csv", csv_data))
            plt.close(fig)
        return figs, svg_files, csv_files

    # --- BACK SCATTER PREVIEW & DOWNLOAD ---
    st.subheader("Back Scatter Distributions")
    back_figs, back_svg_files, back_csv_files = get_plot_and_csvs(["back"]*3, "Back Scatter")
    if back_figs:
        fig, axs = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        for i, f in enumerate(back_figs):
            ax = axs[i]
            tmp = f.axes[0]
            for line in tmp.lines:
                ax.plot(line.get_xdata(), line.get_ydata(),
                        label=line.get_label(), color=line.get_color(),
                        lw=line.get_linewidth(), linestyle=line.get_linestyle())
            ax.set_xlim(tmp.get_xlim())
            ax.set_ylim(tmp.get_ylim())
            ax.set_xticks(tmp.get_xticks())
            ax.set_xticklabels(tmp.get_xticklabels())
            ax.set_xlabel(tmp.get_xlabel())
            ax.set_title(tmp.get_title())
            if i == 0:
                ax.set_ylabel(tmp.get_ylabel())
            ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        # --- DOWNLOAD ZIP ---
        def make_zip(name_pairs):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for fname, data in name_pairs:
                    zf.writestr(fname, data)
            return zip_buffer.getvalue()

        st.download_button(
            label="Download All Back Scatter SVGs (ZIP)",
            data=make_zip(back_svg_files),
            file_name=f"{sheet_selected}_BackScatter_SVGs.zip",
            mime="application/zip"
        )
        st.download_button(
            label="Download All Back Scatter CSVs (ZIP)",
            data=make_zip(back_csv_files),
            file_name=f"{sheet_selected}_BackScatter_CSVs.zip",
            mime="application/zip"
        )

    # --- MADLS PREVIEW & DOWNLOAD ---
    st.subheader("MADLS Distributions")
    madls_figs, madls_svg_files, madls_csv_files = get_plot_and_csvs(["madls"]*3, "MADLS")
    if madls_figs:
        fig, axs = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        for i, f in enumerate(madls_figs):
            ax = axs[i]
            tmp = f.axes[0]
            for line in tmp.lines:
                ax.plot(line.get_xdata(), line.get_ydata(),
                        label=line.get_label(), color=line.get_color(),
                        lw=line.get_linewidth(), linestyle=line.get_linestyle())
            ax.set_xlim(tmp.get_xlim())
            ax.set_ylim(tmp.get_ylim())
            ax.set_xticks(tmp.get_xticks())
            ax.set_xticklabels(tmp.get_xticklabels())
            ax.set_xlabel(tmp.get_xlabel())
            ax.set_title(tmp.get_title())
            if i == 0:
                ax.set_ylabel(tmp.get_ylabel())
            ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.download_button(
            label="Download All MADLS SVGs (ZIP)",
            data=make_zip(madls_svg_files),
            file_name=f"{sheet_selected}_MADLS_SVGs.zip",
            mime="application/zip"
        )
        st.download_button(
            label="Download All MADLS CSVs (ZIP)",
            data=make_zip(madls_csv_files),
            file_name=f"{sheet_selected}_MADLS_CSVs.zip",
            mime="application/zip"
        )

else:
    st.info("Upload POS & NEG Archimedes files, select both, and upload/select a DLS Excel file and condition (sheet) to view plots and downloads.")
