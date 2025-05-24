import streamlit as st
import pandas as pd
import os
import pickle
from datetime import datetime
import openpyxl
from io import BytesIO
import io

# Fungsi menyimpan session state ke file
def simpan_session_state():
    with open("session_state.pkl", "wb") as f:
        pickle.dump(dict(st.session_state), f)

# Fungsi memuat session state dari file
def muat_session_state():
    if os.path.exists("session_state.pkl"):
        with open("session_state.pkl", "rb") as f:
            data = pickle.load(f)
            for k, v in data.items():
                if k not in st.session_state:
                    st.session_state[k] = v
                    
# Fungsi untuk menghapus session state file
def hapus_session_state_file():
    if os.path.exists("session_state.pkl"):
        os.remove("session_state.pkl")

def simpan_semua_ke_excel():
    if not st.session_state.get("jurnal"):
        return None, None

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # --- JURNAL UMUM ---
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        df_jurnal.to_excel(writer, sheet_name="Jurnal Umum", index=False)

        # --- BUKU BESAR ---
        akun_list = df_jurnal["Akun"].unique()
        buku_besar_all = []

        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            df_akun.insert(0, "Nama Akun", akun)  # Tambahkan kolom identifikasi akun
            buku_besar_all.append(df_akun)

        df_buku_besar = pd.concat(buku_besar_all, ignore_index=True)
        df_buku_besar.to_excel(writer, sheet_name="Buku Besar", index=False)

        # --- NERACA SALDO ---
        ref_dict = df_jurnal.groupby("Akun")["Ref"].first().to_dict()

        neraca_saldo = df_jurnal.groupby("Akun")[["Debit", "Kredit"]].sum().reset_index()
        neraca_saldo["Saldo"] = neraca_saldo["Debit"] - neraca_saldo["Kredit"]
        neraca_saldo["Ref"] = neraca_saldo["Akun"].map(ref_dict)
        neraca_saldo = neraca_saldo.sort_values(by="Ref")
        cols = ["Ref", "Akun", "Debit", "Kredit", "Saldo"]
        neraca_saldo = neraca_saldo[cols]
        neraca_saldo.to_excel(writer, sheet_name="Neraca Saldo", index=False)
        
        # --- LABA RUGI ---
        # --- LABA RUGI (Gabung semua kategori + total laba/rugi bersih) ---
        if "data_laba_rugi" in st.session_state:
            laba_rugi_all = []

            for kategori, data in st.session_state.data_laba_rugi.items():
                df = pd.DataFrame(data)
                if not df.empty:
                    df.insert(0, "Kategori", kategori)
                    laba_rugi_all.append(df)

            if laba_rugi_all:
                df_laba_rugi = pd.concat(laba_rugi_all, ignore_index=True)

                # Hitung laba/rugi bersih
                total_pendapatan = df_laba_rugi[df_laba_rugi["Kategori"] == "Pendapatan"]["Nominal"].sum()
                total_beban = df_laba_rugi[df_laba_rugi["Kategori"] != "Pendapatan"]["Nominal"].sum()
                laba_bersih = total_pendapatan - total_beban

                # Tambahkan baris laba/rugi bersih
                df_laba_bersih = pd.DataFrame([{
                    "Kategori": "",
                    "Deskripsi": "Laba/Rugi Bersih",
                    "Nominal": laba_bersih
                }])

                # Gabungkan semua data + laba rugi bersih di akhir
                df_output = pd.concat([df_laba_rugi, pd.DataFrame([{}]), df_laba_bersih], ignore_index=True)
                df_output.to_excel(writer, sheet_name="Laporan Laba Rugi", index=False)

        # --- PERUBAHAN   MODAL ---
        if (
            st.session_state.get("modal_awal") is not None and
            st.session_state.get("laba") is not None and
            st.session_state.get("prive") is not None
        ):
            ekuitas_akhir = (
                st.session_state.modal_awal +
                st.session_state.laba -
                st.session_state.prive
            )
            df_ekuitas = pd.DataFrame([{
                "Modal Awal": st.session_state.modal_awal,
                "Laba": st.session_state.laba,
                "Prive": st.session_state.prive,
                "Ekuitas Akhir": ekuitas_akhir
            }])
            df_ekuitas.to_excel(writer, sheet_name="Perubahan Ekuitas", index=False)

        # --- NERACA (Laporan Posisi Keuangan) ---
        if "neraca" in st.session_state:
            all_data = []
            for kategori, data in st.session_state.neraca.items():
                df = pd.DataFrame(data)
                if not df.empty:
                    df['Kategori'] = kategori  # Tambahkan kolom kategori
                    all_data.append(df)

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df.to_excel(writer, sheet_name="Neraca", index=False)

        # --- JURNAL PENUTUP ---
        if "jurnal_penutup" in st.session_state and st.session_state.jurnal_penutup:
            df_jp = pd.DataFrame(st.session_state.jurnal_penutup)
            if not df_jp.empty:
             df_jp['Kategori'] = "Jurnal Penutup"
            df_jp.to_excel(writer, sheet_name="Jurnal Penutup", index=False)

         # --- NERACA SALDO SETELAH PENUTUPAN (NSSP) ---
        if "neraca_saldo_setelah_penutupan" in st.session_state and st.session_state.neraca_saldo_setelah_penutupan:
            df_nssp = pd.DataFrame(st.session_state.neraca_saldo_setelah_penutupan)
            if not df_nssp.empty:
             df_nssp['Kategori'] = "NSSP"
            df_nssp.to_excel(writer, sheet_name="NSSP", index=False)


    buffer.seek(0)
    filename = "laporan_keuangan.xlsx"
    return buffer, filename

# Ambil tanggal pertama dari jurnal
    df_jurnal = pd.DataFrame(st.session_state.jurnal)
    tanggal_pertama = pd.to_datetime(df_jurnal["Tanggal"]).min().strftime("%d-%b-%Y")

    # Buat nama file
    nama_file = f"laporan_keuangan_{tanggal_pertama}.xlsx"

    with(nama_file,"openpyxl") as writer:

        # Simpan Jurnal Umum
        df_jurnal(writer, sheet_name="Jurnal Umum", index=False)

        # Buku Besar
        akun_list = df_jurnal["Akun"].unique() 
        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            df_akun(writer, sheet_name=f"Buku Besar - {akun[:30]}", index=False)

        # Neraca Saldo
        neraca_saldo = df_jurnal.groupby("Akun")[["Debit", "Kredit"]].sum().reset_index()
        neraca_saldo["Saldo"] = neraca_saldo["Debit"] - neraca_saldo["Kredit"]
        neraca_saldo(writer, sheet_name="Neraca Saldo", index=False)

        # Laba Rugi
        if "data_laba_rugi" in st.session_state:
            for kategori, data in st.session_state.data_laba_rugi.items():
                df = pd.DataFrame(data)
                if not df.empty:
                    df(writer, sheet_name=f"Laba Rugi - {kategori[:30]}", index=False)

        # Perubahan Modal
        if st.session_state.modal_awal is not None:
            df_ekuitas = pd.DataFrame([{
                "Modal Awal": st.session_state.modal_awal,
                "Laba": st.session_state.laba,
                "Prive": st.session_state.prive,
                "Modal Akhir": st.session_state.modal_awal + st.session_state.laba - st.session_state.prive
            }])
            df_ekuitas(writer, sheet_name="Perubahan Modal", index=False)

        # Laporan Posisi Keuangan (Neraca)
        if "Laporan posisi keuangan" in st.session_state:
            for kategori, data in st.session_state["posisi keuangan"].items():
                df = pd.DataFrame(data)
                if not df.empty:
                    df(writer, sheet_name=f"Laporan posisi keuangan - {kategori[:30]}", index=False)

        # Jurnal Penutup
        if "jurnal_penutup" in st.session_state and st.session_state.jurnal_penutup:
            df_jurnal_penutup = pd.DataFrame(st.session_state.jurnal_penutup)
            df_jurnal_penutup(writer, sheet_name="Jurnal Penutup", index=False)

        # Neraca Saldo Setelah Penutupan (NSSP)
        if "neraca_saldo_setelah_penutupan" in st.session_state:
            df_nssp = pd.DataFrame(st.session_state.neraca_saldo_setelah_penutupan)
            if not df_nssp.empty :
                df_nssp(writer, sheet_name="NSSP", index=False)

    return name_file


# === PANGGIL DI SINI (SEBELUM st.title(), st.sidebar, dst.) ===
muat_session_state()

st.set_page_config(page_title="LAPORAN KEUANGAN TERNAK TELUR🐣 WRINGINPUTIH", layout="wide")
st.title("LAPORAN KEUANGAN TERNAK TELUR🐣 PUYUH WRINGINPUTIH")

st.sidebar.markdown("<h2 style='text-align: center;'><br>LAPORAN KEUANGAN<br>WRINGINPUTIH</h2>", unsafe_allow_html=True)

menu = st.sidebar.radio("Pilih Navigasi:", (
    "Beranda",
    "Jurnal Umum",
    "Buku Besar",
    "Neraca Saldo",
    "Laporan Laba Rugi",
    "Laporan Perubahan Modal",
    "Laporan Posisi Keuangan",
    "Jurnal Penutup",
    "NSSP",
    "Unduh Data"

))

# Initialize session state variables if not already set
if "modal_awal" not in st.session_state:
    st.session_state.modal_awal = None  # or False/True/"" based on your logic


    # Buku Besar, Neraca Saldo, Laba Rugi, Perubahan Modal, Posisi Keuangan, Jurnal Penutup, dan NSSP
    # Bagian ini sebelumnya mencoba menggunakan 'writer' yang tidak didefinisikan.
    # Jika Anda ingin mengekspor ke Excel, gunakan fungsi ekspor yang sudah ada di atas (fungsi yang membuat ExcelWriter).
    # Jika tidak, hapus saja blok ini karena tidak diperlukan di sini.


if menu == "Beranda":
    st.title("Selamat Datang di Laporan Keuangan WRINGINPUTIH")
    st.markdown("""
        ### Tentang Aplikasi
        Aplikasi ini membantu Anda mencatat dan menyusun laporan keuangan secara sederhana dan efisien.  
        Anda dapat mengelola:
        - Jurnal Umum
        - Buku Besar
        - Neraca Saldo
        - Laporan Laba Rugi
        - Perubahan Modal
        - Laporan Posisi Keuangan
        - Jurnal Penutup
        - NSSP (Neraca Saldo Setelah Penutupan)
        - Unduh Data

        ### Petunjuk Penggunaan
        1. Masukkan transaksi melalui Jurnal Umum.
        2. Data akan otomatis terhubung ke Buku Besar dan Neraca Saldo.
        3. Untuk laporan laba rugi, perubahan ekuitas dan neraca, gunakan menu input manual.
        4. Gunakan tombol reset di tiap halaman untuk memulai data baru.

        ### Catatan
        - Pastikan jurnal Anda seimbang (total debit = total kredit).
        - Pastikan menginput dengan teliti dan cek secara berkala.
    """)

    st.info("Gunakan menu di sidebar untuk mulai mencatat dan melihat laporan keuangan Anda.")

# --- JURNAL UMUM ---
if menu == "Jurnal Umum":
    st.header("Jurnal Umum")
    if "jurnal" not in st.session_state:
        st.session_state.jurnal = []

    with st.form("form_jurnal"):
        st.subheader("Input Transaksi Jurnal")
        tanggal = st.date_input("Tanggal", value=datetime.today())
        keterangan = st.text_input("Akun")
        akun = st.text_input("Ref")
        debit = st.number_input("Debit", min_value=0.0, format="%.2f")
        kredit = st.number_input("Kredit", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Tambah")

        if submitted:
            if akun:
                st.session_state.jurnal.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Akun": keterangan,
                    "Ref": akun,
                    "Debit": debit,
                    "Kredit": kredit
                })
                simpan_session_state()
            else:
                st.warning("Nama akun tidak boleh kosong!")

    if st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        st.dataframe(df_jurnal, use_container_width=True)
        st.subheader("Edit Jurnal Jika Perlu:")
        df_edit = st.data_editor(df_jurnal, num_rows="dynamic", use_container_width=True, key="edit_jurnal")
        if st.button("Simpan Perubahan Jurnal"):
            st.session_state.jurnal = df_edit.to_dict(orient="records")
            simpan_session_state()
            st.success("Perubahan jurnal berhasil disimpan.")

        total_debit = df_jurnal["Debit"].sum()
        total_kredit = df_jurnal["Kredit"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Total Debit", f"{total_debit:,.2f}")
        col2.metric("Total Kredit", f"{total_kredit:,.2f}")

        if total_debit == total_kredit:
            st.success("Jurnal seimbang!")
        else:
            st.error("Jurnal tidak seimbang!")

    if st.button("Reset Semua Data"):
        st.session_state.jurnal = []
        hapus_session_state_file()
        st.success("Data jurnal berhasil direset.")
        st.rerun()

# --- BUKU BESAR ---
elif menu == "Buku Besar":
    st.header("Buku Besar")

    if "jurnal" not in st.session_state or not st.session_state.jurnal:
        st.info("Belum ada data jurnal.")
    else:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        akun_unik = df_jurnal["Akun"].unique()
        akun_dipilih = st.selectbox("Pilih Akun", akun_unik)

        df_akun = df_jurnal[df_jurnal["Akun"] == akun_dipilih].copy()
        df_akun["Saldo"] = (df_akun["Debit"] - df_akun["Kredit"]).cumsum()

        st.subheader(f"Buku Besar: {akun_dipilih}")
        st.dataframe(df_akun[["Tanggal", "Ref", "Debit", "Kredit", "Saldo"]], use_container_width=True)

        total_debit = df_akun["Debit"].sum()
        total_kredit = df_akun["Kredit"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Total Debit", f"{total_debit:,.2f}")
        col2.metric("Total Kredit", f"{total_kredit:,.2f}")


# --- NERACA SALDO ---
elif menu == "Neraca Saldo":
    st.header("Neraca Saldo")

    if "jurnal" in st.session_state and st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal).sort_values(by=["Ref", "Tanggal"])

        # Hitung saldo akumulatif terakhir per akun
        akun_list = df_jurnal["Akun"].unique()
        saldo_akhir_list = []

        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            saldo_akhir = df_akun["Saldo Akumulatif"].iloc[-1]

            # Ambil referensi dari entri pertama akun tsb
            ref = df_akun["Ref"].iloc[0]

            # Bagi ke debit/kredit sesuai saldo
            debit = saldo_akhir if saldo_akhir >= 0 else 0
            kredit = -saldo_akhir if saldo_akhir < 0 else 0

            saldo_akhir_list.append({
                "Ref": ref,
                "Akun": akun,
                "Debit": debit,
                "Kredit": kredit
            })

        df_saldo = pd.DataFrame(saldo_akhir_list)
        df_saldo = df_saldo.sort_values(by="Ref")

        total_debit = df_saldo["Debit"].sum()
        total_kredit = df_saldo["Kredit"].sum()

        # Tambahkan baris total
        total_row = pd.DataFrame({
            "Ref": ["TOTAL"],
            "Akun": [""],
            "Debit": [total_debit],
            "Kredit": [total_kredit]
        })

        df_saldo_tampil = pd.concat([df_saldo, total_row], ignore_index=True)

        st.dataframe(df_saldo_tampil[["Ref", "Akun", "Debit", "Kredit"]], use_container_width=True)

        # Validasi keseimbangan
        if total_debit == total_kredit:
            st.success("✅ Neraca Saldo Seimbang")
        else:
            st.error(f"❌ Neraca Saldo Tidak Seimbang — Selisih: Rp {abs(total_debit - total_kredit):,.2f}")

    else:
        st.info("Belum ada data jurnal untuk dihitung.")


# --- LAPORAN LABA RUGI ---
elif menu == "Laporan Laba Rugi":
    st.header("Laporan Laba Rugi")

    # --- KATEGORI ---
    kategori_list = ["Pendapatan", "Beban Listrik dan air"]

    # --- INISIALISASI SESSION STATE ---
    if "data_laba_rugi" not in st.session_state or not isinstance(st.session_state.data_laba_rugi, dict):
        st.session_state.data_laba_rugi = {}
    for kategori in kategori_list:
        if kategori not in st.session_state.data_laba_rugi:
            st.session_state.data_laba_rugi[kategori] = []

    # --- TABS: INPUT & LAPORAN ---
    tab1, tab2 = st.tabs(["Input Transaksi", "Laporan Laba Rugi"])

    # --- TAB INPUT TRANSAKSI ---
    with tab1:
        st.subheader("Input Transaksi Laba Rugi")
        kategori = st.selectbox("Kategori", kategori_list)
        deskripsi = st.text_input("Deskripsi")
        nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)

        if st.button("Tambah Transaksi"):
            if deskripsi and nominal > 0:
                st.session_state.data_laba_rugi[kategori].append({
                    "Deskripsi": deskripsi,
                    "Nominal": nominal
                })
                simpan_session_state()
                st.success(f"Transaksi {kategori} berhasil ditambahkan.")
            else:
                st.warning("Mohon isi deskripsi dan nominal dengan benar.")

    # --- TAB LAPORAN LABA RUGI ---
    with tab2:
        total_pendapatan = 0
        total_beban = 0

        st.subheader("Pendapatan")
        df_pendapatan = pd.DataFrame(st.session_state.data_laba_rugi["Pendapatan"])
        if not df_pendapatan.empty:
            df_edit = st.data_editor(
                df_pendapatan,
                num_rows="dynamic",
                use_container_width=True,
                key="edit_pendapatan"
            )
            if st.button("Simpan Perubahan Pendapatan"):
                st.session_state.data_laba_rugi["Pendapatan"] = df_edit.to_dict(orient="records")
                simpan_session_state()
                st.success("Perubahan pendapatan berhasil disimpan.")
            total_pendapatan = df_pendapatan["Nominal"].sum()
        else:
            st.info("Belum ada data pendapatan.")
        st.write(f"Total Pendapatan: Rp {total_pendapatan:,.0f}")

        # Loop setiap kategori beban
        for i, kategori in enumerate(kategori_list[1:], start=1):
            st.subheader(kategori)
            df_beban = pd.DataFrame(st.session_state.data_laba_rugi[kategori])
            if not df_beban.empty:
                df_edit = st.data_editor(
                    df_beban,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"edit_beban_{i}"
                )
                if st.button(f"Simpan Perubahan {kategori}", key=f"simpan_beban_{i}"):
                    st.session_state.data_laba_rugi[kategori] = df_edit.to_dict(orient="records")
                    simpan_session_state()
                    st.success(f"Perubahan {kategori} berhasil disimpan.")
                subtotal = df_beban["Nominal"].sum()
            else:
                st.info(f"Belum ada data {kategori.lower()}.")
                subtotal = 0
            total_beban += subtotal
            st.write(f"Total {kategori}: Rp {subtotal:,.0f}")

        # --- LABA / RUGI BERSIH ---
        laba_rugi = total_pendapatan - total_beban
        st.markdown("---")
        st.metric("Laba / Rugi Bersih", f"Rp {laba_rugi:,.0f}")

        # --- RESET SEMUA DATA ---
        if st.button("Reset Semua Data Laba Rugi"):
            for kategori in kategori_list:
                st.session_state.data_laba_rugi[kategori] = []
            hapus_session_state_file()
            st.success("Semua data laba rugi berhasil direset.")
            st.rerun()

# --- PERUBAHAN MODAL ---
elif menu == "Laporan Perubahan Modal":
    st.header("Laporan Perubahan Modal")

    struktur_modal = {
        "Modal Awal": [],
        "Laba Ditahan": [],
        "Prive": []
    }

    if "perubahan_modal" not in st.session_state:
        st.session_state.perubahan_modal = {kategori: [] for kategori in struktur_modal}

    tab1, tab2 = st.tabs(["Input Manual", "Laporan Perubahan Modal"])

    # --- TAB INPUT MANUAL ---
    with tab1:
        kategori = st.selectbox("Kategori", list(st.session_state.perubahan_modal.keys()))
        nama_item = st.text_input("Nama Item")
        nilai = st.number_input("Nilai (Rp)", min_value=0, step=1000)

        if st.button("Tambah Item Modal"):
            if nama_item and nilai > 0:
                st.session_state.perubahan_modal[kategori].append({"Item": nama_item, "Nilai": nilai})
                simpan_session_state()
                st.success(f"{nama_item} berhasil ditambahkan ke {kategori}.")
            else:
                st.warning("Harap isi nama item dan nilai yang valid.")

    # --- TAB LAPORAN PERUBAHAN MODAL ---
    with tab2:
        total_modal_awal = 0
        total_laba_ditahan = 0
        total_prive = 0

        for i, kategori in enumerate(st.session_state.perubahan_modal.keys()):
            st.markdown(f"### {kategori}")
            df = pd.DataFrame(st.session_state.perubahan_modal[kategori])
            if not df.empty:
                df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_modal_{i}")
                if st.button(f"Simpan Perubahan {kategori}", key=f"simpan_modal_{i}"):
                    st.session_state.perubahan_modal[kategori] = df_edit.to_dict(orient="records")
                    simpan_session_state()
                    st.success(f"Perubahan {kategori} berhasil disimpan.")
                subtotal = df_edit["Nilai"].sum()
            else:
                st.info(f"Belum ada data untuk {kategori}.")
                subtotal = 0

            if kategori == "Modal Awal":
                total_modal_awal += subtotal
            elif kategori == "Laba Ditahan":
                total_laba_ditahan += subtotal
            elif kategori == "Prive":
                total_prive += subtotal

            st.write(f"Subtotal {kategori}: Rp {subtotal:,.0f}")

        st.markdown("---")

        # --- PERHITUNGAN MODAL AKHIR ---
        modal_akhir = total_modal_awal + total_laba_ditahan - total_prive
        st.metric("Modal Akhir", f"Rp {modal_akhir:,.0f}")

        # --- TOMBOL RESET ---
        if st.button("Reset Semua Data", key="reset_perubahan_modal"):
            st.session_state.perubahan_modal = {kategori: [] for kategori in struktur_modal}
            simpan_session_state()
            st.success("Semua data perubahan modal berhasil direset.")
            st.rerun()

# --- NERACA (LAPORAN POSISI KEUANGAN) ---
elif menu == "Laporan Posisi Keuangan":
    st.header("Laporan Posisi Keuangan")

    struktur = {"Aktiva Lancar": [], "Aktiva Tetap": [], "Kewajiban": [], "Ekuitas": []}
    if "neraca" not in st.session_state:
        st.session_state.neraca = {kategori: [] for kategori in struktur}

    tab1, tab2 = st.tabs(["Input Manual", "Laporan Posisi Keuangan"])

    # Tab Input Manual
    with tab1:
        kategori = st.selectbox("Kategori", list(st.session_state.neraca.keys()))
        nama_akun = st.text_input("Nama Akun")
        nilai = st.number_input("Nilai (Rp)", min_value=0, step=1000)

        if st.button("Tambah Akun"):
            if nama_akun and nilai > 0:
                st.session_state.neraca[kategori].append({"Akun": nama_akun, "Nilai": nilai})
                simpan_session_state()
                st.success(f"{nama_akun} berhasil ditambahkan ke {kategori}.")
            else:
                st.warning("Harap isi nama akun dan nilai yang valid.")

    # Tab Laporan Posisi Keuangan (dengan editor)
    with tab2:
        col1, col2 = st.columns(2)
        total_aktiva = 0

        with col1:
            st.subheader("Aktiva")
            for kategori in ["Aktiva Lancar", "Aktiva Tetap"]:
                st.markdown(f"### {kategori}")
                df = pd.DataFrame(st.session_state.neraca[kategori])
                if not df.empty:
                    df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_{kategori}")
                    if st.button(f"Simpan Perubahan {kategori}", key=f"simpan_{kategori}"):
                        st.session_state.neraca[kategori] = df_edit.to_dict(orient="records")
                        simpan_session_state()
                        st.success(f"Perubahan {kategori} berhasil disimpan.")
                    subtotal = df_edit["Nilai"].sum()
                    total_aktiva += subtotal
                    st.write(f"Subtotal {kategori}: Rp {subtotal:,.0f}")
                else:
                    st.info(f"Tidak ada data untuk {kategori}")
            st.markdown(f"Total Aktiva: Rp {total_aktiva:,.0f}")

        total_pasiva = 0
        with col2:
            st.subheader("Pasiva")
            for kategori in ["Kewajiban", "Ekuitas"]:
                st.markdown(f"### {kategori}")
                df = pd.DataFrame(st.session_state.neraca[kategori])
                if not df.empty:
                    df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_{kategori}")
                    if st.button(f"Simpan Perubahan {kategori}", key=f"simpan_{kategori}"):
                        st.session_state.neraca[kategori] = df_edit.to_dict(orient="records")
                        simpan_session_state()
                        st.success(f"Perubahan {kategori} berhasil disimpan.")
                    subtotal = df_edit["Nilai"].sum()
                    total_pasiva += subtotal
                    st.write(f"Subtotal {kategori}: Rp {subtotal:,.0f}")
                else:
                    st.info(f"Tidak ada data untuk {kategori}")
            st.markdown(f"Total Pasiva: Rp {total_pasiva:,.0f}")

        # Validasi neraca
        if total_aktiva == total_pasiva:
            st.success("Neraca Seimbang")
        else:
            st.error(f"Selisih Neraca: Rp {abs(total_aktiva - total_pasiva):,.0f}")

        # Tombol reset
        if st.button("Reset Semua Data", key="reset_button_2"):
            st.session_state.neraca = {kategori: [] for kategori in struktur}
            simpan_session_state()
            st.success("Semua data berhasil direset.")


# --- JURNAL PENUTUP ---
elif menu == "Jurnal Penutup":
    st.header("Jurnal Penutup")

    if "jurnal_penutup" not in st.session_state:
        st.session_state.jurnal_penutup = []

    tab1, tab2 = st.tabs(["Input Manual", "Jurnal Penutup"])

    with tab1:
        tanggal = st.date_input("Tanggal Penutupan", value=datetime.today())
        akun = st.text_input("Nama Akun (yang ditutup)")
        debit = st.number_input("Debit", min_value=0, step=1000, key="debit_penutup")
        kredit = st.number_input("Kredit", min_value=0, step=1000, key="kredit_penutup")

        if st.button("Tambah Jurnal Penutup"):
            if akun and (debit > 0 or kredit > 0):
                st.session_state.jurnal_penutup.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Akun": akun,
                    "Debit": debit,
                    "Kredit": kredit
                })
                simpan_session_state()
                st.success(f"Jurnal penutup untuk akun '{akun}' berhasil ditambahkan.")
            else:
                st.warning("Harap isi akun dan nominal debit/kredit.")

    with tab2:
        if st.session_state.jurnal_penutup:
            df_jp = pd.DataFrame(st.session_state.jurnal_penutup)
            df_edit = st.data_editor(df_jp, num_rows="dynamic", use_container_width=True, key="jp_editor")

            if st.button("Simpan Perubahan Jurnal Penutup"):
                st.session_state.jurnal_penutup = df_edit.to_dict(orient="records")
                simpan_session_state()
                st.success("Perubahan disimpan.")

            st.write("Total Debit: Rp {:,.0f}".format(df_edit["Debit"].sum()))
            st.write("Total Kredit: Rp {:,.0f}".format(df_edit["Kredit"].sum()))
        else:
            st.info("Belum ada jurnal penutup yang dimasukkan.")

# --- NERACA SALDO SETELAH PENUTUPAN ---
elif menu == "NSSP":
    st.header("Neraca Saldo Setelah Penutupan")

    if "neraca_saldo_setelah_penutupan" not in st.session_state:
        st.session_state.neraca_saldo_setelah_penutupan = []

    tab1, tab2 = st.tabs(["Input Manual", "Tampilan NSSP"])

    with tab1:
        akun = st.text_input("Nama Akun")
        debit = st.number_input("Debit (Rp)", min_value=0, step=1000, key="debit_nssp")
        kredit = st.number_input("Kredit (Rp)", min_value=0, step=1000, key="kredit_nssp")

        if st.button("Tambah ke NSSP"):
            if akun and (debit > 0 or kredit > 0):
                st.session_state.neraca_saldo_setelah_penutupan.append({
                    "Akun": akun,
                    "Debit": debit,
                    "Kredit": kredit
                })
                simpan_session_state()
                st.success(f"Akun '{akun}' berhasil ditambahkan ke NSSP.")
            else:
                st.warning("Harap isi akun dan nilai debit/kredit.")

    with tab2:
        if st.session_state.neraca_saldo_setelah_penutupan:
            df_nssp = pd.DataFrame(st.session_state.neraca_saldo_setelah_penutupan)
            df_edit = st.data_editor(df_nssp, num_rows="dynamic", use_container_width=True, key="nssp_editor")

            if st.button("Simpan Perubahan NSSP"):
                st.session_state.neraca_saldo_setelah_penutupan = df_edit.to_dict(orient="records")
                simpan_session_state()
                st.success("Perubahan disimpan.")

            st.write("Total Debit: Rp {:,.0f}".format(df_edit["Debit"].sum()))
            st.write("Total Kredit: Rp {:,.0f}".format(df_edit["Kredit"].sum()))

            if df_edit["Debit"].sum() == df_edit["Kredit"].sum():
                st.success("NSSP Seimbang ✅")
            else:
                st.error("⚠ NSSP Tidak Seimbang")
        else:
            st.info("Belum ada data NSSP yang dimasukkan.")
       
# --- UNDUH DATA ---
elif menu == "Unduh Data":
    st.title("Unduh Laporan Keuangan")

    if st.button("Simpan ke Excel"):
        excel_io, filename = simpan_semua_ke_excel()
        if excel_io:
            st.session_state.excel_io = excel_io
            st.session_state.excel_filename = filename
            st.success("File berhasil dibuat, silakan unduh di bawah.")
        else:
            st.warning("Tidak ada data jurnal untuk disimpan.")

    if "excel_io" in st.session_state and "excel_filename" in st.session_state:
        st.download_button(
            label="📥 Unduh Laporan Keuangan Excel",
            data=st.session_state.excel_io,
            file_name=st.session_state.excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Klik tombol 'Simpan ke Excel' terlebih dahulu untuk membuat file.")
