import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="TO P2TL AMR", layout="wide")

# -------------------------
# Halaman Login
# -------------------------
def login():
    st.title("🔐 Sistem Otomatisasi Penyusunan Target Operasi P2TL")
    st.subheader("Silakan masuk untuk melanjutkan")

    username = st.text_input("👤 Username")
    password = st.text_input("🔒 Password", type="password")

    if st.button("Login"):
        if username == "fauzihidayat" and password == "lancarBarokah":
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Username atau Password salah.")

# -------------------------
# Aplikasi Utama
# -------------------------
def main():
    st.title("📊 Dashboard Target Operasi P2TL AMR Periode June 2025")

    uploaded_file = st.file_uploader("Upload File INSTANT (XLSX/CSV)", type=["xlsx", "csv"])

    if not uploaded_file:
        st.warning("⚠️ Data Instant Belum di Upload")
        return

    try:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.success("✅ Data berhasil dimuat.")
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return

    # -------------------------
    # Pengaturan Threshold
    # -------------------------
    with st.expander("⚙️ Setting Parameter", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            tm_vdrop = st.number_input("Tegangan Drop TM", value=56.0)
            tm_ovolt = st.number_input("Over Voltage TM", value=62.0)

        with col2:
            tm_cosphi = st.number_input("Cos Phi TM Maks", value=0.4)
            arus_p_lost = st.number_input("Batas Arus P Lost", value=0.5)

        with col3:
            unbalance_tol = st.number_input("Toleransi Unbalance", value=0.5)
            netral_vs_fasa = st.number_input("Netral > Fasa (x%)", value=1.3)
            imp_gt_exp = st.checkbox("Import > Export")
            v_lost_ada_arus = st.checkbox("Tegangan Hilang saat Ada Arus")

    # -------------------------
    # Logika Deteksi Anomali
    # -------------------------
    df_result = df.copy()
    df_result["v_drop"] = df_result["VOLTAGE_L1"] < tm_vdrop
    df_result["cos_phi_kecil"] = df_result["COS_PHI"] < tm_cosphi
    df_result["over_voltage"] = df_result["VOLTAGE_L1"] > tm_ovolt
    df_result["active_p_lost"] = (df_result["ACTIVE_POWER"] == 0) & (df_result["CURRENT_L1"] > arus_p_lost)
    df_result["unbalance_I"] = abs(df_result["CURRENT_L1"] - df_result[["CURRENT_L2", "CURRENT_L3"]].mean(axis=1)) >= unbalance_tol
    df_result["in_more_Imax"] = df_result["CURRENT_N"] > df_result[["CURRENT_L1", "CURRENT_L2", "CURRENT_L3"]].max(axis=1) * netral_vs_fasa
    df_result["import_gt_export"] = (df_result["KWH_IMP"] > df_result["KWH_EXP"]) if imp_gt_exp else False
    df_result["v_lost_ada_arus"] = (df_result["VOLTAGE_L1"] == 0) & (df_result["CURRENT_L1"] > 0) if v_lost_ada_arus else False

    indikator_cols = ["v_drop", "cos_phi_kecil", "over_voltage", "active_p_lost",
                      "unbalance_I", "in_more_Imax", "import_gt_export", "v_lost_ada_arus"]

    df_result["jumlah_potensi"] = df_result[indikator_cols].sum(axis=1)
    df_result["bobot"] = df_result["jumlah_potensi"] * 5

    # -------------------------
    # Kriteria TO
    # -------------------------
    with st.expander("📋 Kriteria TO", expanded=True):
        min_indikator = st.number_input("Jumlah Indikator Minimal", min_value=1, value=2)
        min_bobot = st.number_input("Jumlah Bobot Minimal", min_value=1, value=10)
        top_n = st.number_input("Tampilkan Top-N", min_value=1, value=50)

    df_result["status_TO"] = (df_result["jumlah_potensi"] >= min_indikator) & (df_result["bobot"] >= min_bobot)

    top = df_result[df_result["status_TO"]].sort_values(by="bobot", ascending=False).head(top_n)

    # -------------------------
    # Visualisasi Checkbox
    # -------------------------
    def render_check(val):
        return "✅" if val else ""

    top_display = top[["IDPEL", "NAMA", "TARIF", "DAYA"] + indikator_cols + ["jumlah_potensi", "bobot"]].copy()
    for col in indikator_cols:
        top_display[col] = top_display[col].apply(render_check)

    st.dataframe(top_display, use_container_width=True)

    # -------------------------
    # Ekspor ke Excel
    # -------------------------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        top_display.to_excel(writer, index=False, sheet_name="TO_Analysis")
    st.download_button("📤 Download Hasil Analisis", output.getvalue(), "hasil_analisis_to_amr.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -------------------------
# Routing Halaman
# -------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    main()
