import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import zipfile

# ... (previous upload and processing code stays the same)

# --- Download Helper ---
def make_zip(name_pairs):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for fname, data in name_pairs:
            zf.writestr(fname, data)
    return zip_buffer.getvalue()

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
    # SVG download (as 1x3 panel)
    svg_buf = io.StringIO()
    fig.savefig(svg_buf, format="svg", bbox_inches='tight')
    st.download_button(
        label="Download Back Scatter (1x3 SVG)",
        data=svg_buf.getvalue(),
        file_name=f"{sheet_selected}_BackScatter_1x3.svg",
        mime="image/svg+xml"
    )
    plt.close(fig)
    # CSVs as ZIP
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
    # SVG download (as 1x3 panel)
    svg_buf = io.StringIO()
    fig.savefig(svg_buf, format="svg", bbox_inches='tight')
    st.download_button(
        label="Download MADLS (1x3 SVG)",
        data=svg_buf.getvalue(),
        file_name=f"{sheet_selected}_MADLS_1x3.svg",
        mime="image/svg+xml"
    )
    plt.close(fig)
    # CSVs as ZIP
    st.download_button(
        label="Download All MADLS CSVs (ZIP)",
        data=make_zip(madls_csv_files),
        file_name=f"{sheet_selected}_MADLS_CSVs.zip",
        mime="application/zip"
    )
