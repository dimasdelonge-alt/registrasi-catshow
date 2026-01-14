import streamlit as st
import pandas as pd
import os
import io

# --- LIBRARY PDF BARU ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Registrasi Catshow", page_icon="🏆", layout="wide")

FILE_DATABASE = 'data_peserta_catshow.csv'

# --- INISIALISASI SESSION ---
if 'form_key' not in st.session_state:
    st.session_state['form_key'] = 0

def reset_form():
    st.session_state['form_key'] += 1

# --- FUNGSI LOAD & SAVE ---
def load_data():
    if os.path.exists(FILE_DATABASE):
        df = pd.read_csv(FILE_DATABASE)
        if 'Jenis Kelamin' not in df.columns:
            df['Jenis Kelamin'] = '-'
        return df
    else:
        return pd.DataFrame(columns=[
            "Nama Pemilik", "No HP", "Nama Kucing", "Jenis Kelamin", "Ras", "Warna", 
            "Status", "Kategori Umur", "Kelas Lomba"
        ])

def save_overwrite(df_new):
    df_new.to_csv(FILE_DATABASE, index=False)
    return df_new

def add_data(data_baru):
    df_lama = load_data()
    df_update = pd.concat([df_lama, data_baru], ignore_index=True)
    df_update.to_csv(FILE_DATABASE, index=False)
    return df_update

# --- FUNGSI GENERATE PDF (GRID 8 ID CARD) ---
@st.cache_data
def generate_number_tags(df_input, current_show_type):
    # 1. SIAPKAN DATA
    df = df_input.copy()
    
    # Logic Sorting
    def get_group_rank(ras_val):
        if ras_val == "Domestik": return 3
        elif ras_val == "Household Pet (Mix)": return 2
        else: return 1 
    def get_status_rank(status_val):
        if status_val == "Pedigree": return 1
        elif status_val == "Non-Pedigree": return 2
        else: return 3
    
    df['Rank_Group'] = df['Ras'].apply(get_group_rank)
    df['Rank_Status'] = df['Status'].apply(get_status_rank)
    
    if "Tipe 1" in current_show_type:
        sort_keys = ['Rank_Group', 'Rank_Status', 'Ras', 'Warna']
    else:
        sort_keys = ['Rank_Group', 'Ras', 'Rank_Status', 'Warna']

    df = df.sort_values(by=sort_keys, ascending=[True]*len(sort_keys))
    
    # 2. SETUP CANVAS PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4 # A4: 210 x 297 mm
    
    # --- KONFIGURASI GRID (8 KOTAK: 2 Kolom x 4 Baris) ---
    margin_left = 10 * mm
    margin_top = 10 * mm
    cols = 2
    rows = 4
    
    # Hitung Lebar/Tinggi per Kotak
    box_w = (width - (2 * margin_left)) / cols  
    box_h = (height - (2 * margin_top)) / rows 
    
    logo_path = "logo.png"
    has_logo = os.path.exists(logo_path)

    # 3. LOOPING
    x_start = margin_left
    y_start = height - margin_top - box_h
    
    col_counter = 0
    row_counter = 0
    
    for i in range(len(df)):
        nomor_urut = str(i + 1)
        row_data = df.iloc[i]
        
        # --- BACKGROUND & BORDER ---
        c.setLineWidth(1)
        c.rect(x_start, y_start, box_w, box_h)
        
        # --- 1. HEADER (KOP) ---
        header_h = 15 * mm # Tinggi area header
        header_y_base = y_start + box_h - header_h
        
        # Garis pembatas header
        c.setLineWidth(0.5)
        c.line(x_start + 2*mm, header_y_base, x_start + box_w - 2*mm, header_y_base)
        
        # Logo & Tulisan
        if has_logo:
            c.drawImage(logo_path, x_start + 5*mm, header_y_base + 3*mm, width=10*mm, height=10*mm, mask='auto')
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_start + 18*mm, header_y_base + 8*mm, "SMART GROOMER")
            c.drawString(x_start + 18*mm, header_y_base + 4*mm, "INDONESIA")
        else:
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x_start + (box_w/2), header_y_base + 6*mm, "SMART GROOMER INDONESIA")

        # Info Kelas Kecil di Pojok Kanan Atas
        c.setFont("Helvetica", 8)
        c.drawRightString(x_start + box_w - 5*mm, header_y_base + 4*mm, f"Kelas: {row_data['Kategori Umur']}")

        # --- 2. NOMOR URUT (CENTER BIG) ---
        # Area tengah
        c.setFont("Helvetica-Bold", 45) # Ukuran Font Besar
        c.drawCentredString(x_start + (box_w/2), y_start + (box_h/2) + 5*mm, nomor_urut)
        
        # --- 3. DETAIL INFO (BAWAH) ---
        detail_y_start = y_start + 15*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_start + 5*mm, detail_y_start + 5*mm, f"Name : {str(row_data['Nama Kucing'])[:20]}") # Potong jika kepanjangan
        
        c.setFont("Helvetica", 9)
        c.drawString(x_start + 5*mm, detail_y_start, f"Breed : {row_data['Ras']} ({row_data['Warna']})")
        c.drawString(x_start + 5*mm, detail_y_start - 5*mm, f"Sex    : {row_data['Jenis Kelamin']}")

        # --- LOGIKA PINDAH KOTAK ---
        x_start += box_w
        col_counter += 1
        
        if col_counter >= cols: # Pindah Baris
            col_counter = 0
            x_start = margin_left
            y_start -= box_h
            row_counter += 1
            
        if row_counter >= rows: # Ganti Halaman
            c.showPage()
            x_start = margin_left
            y_start = height - margin_top - box_h
            row_counter = 0
            col_counter = 0

    c.save()
    return buffer.getvalue()

# --- FUNGSI EXPORT EXCEL (TETAP SAMA) ---
def to_excel_styled(df_input, current_show_type):
    df = df_input.copy()
    
    def get_group_rank(ras_val):
        if ras_val == "Domestik": return 3
        elif ras_val == "Household Pet (Mix)": return 2
        else: return 1 
    def get_age_rank(umur_val):
        if "Kitten" in str(umur_val): return 1
        else: return 2
    def get_status_rank(status_val):
        if status_val == "Pedigree": return 1
        elif status_val == "Non-Pedigree": return 2
        else: return 3

    df['Rank_Group'] = df['Ras'].apply(get_group_rank)
    df['Rank_Age'] = df['Kategori Umur'].apply(get_age_rank)
    df['Rank_Status'] = df['Status'].apply(get_status_rank)
    
    if "Tipe 1" in current_show_type:
        sort_keys = ['Rank_Group', 'Rank_Status', 'Rank_Age', 'Ras', 'Warna']
    else:
        sort_keys = ['Rank_Group', 'Ras', 'Rank_Status', 'Rank_Age', 'Warna']

    df = df.sort_values(by=sort_keys, ascending=[True]*len(sort_keys))
    df.insert(0, 'No', range(1, 1 + len(df)))
    df = df.drop(columns=['Rank_Group', 'Rank_Age', 'Rank_Status'])

    cols_final = ["No", "Nama Pemilik", "No HP", "Nama Kucing", "Jenis Kelamin", "Ras", "Warna", "Status", "Kategori Umur", "Kelas Lomba"]
    if "Tipe 2" in current_show_type:
        cols_final.remove("Status")

    output = io.BytesIO()
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    wb = workbook.book
    
    fmt_title = wb.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#DDEBF7'})
    fmt_header = wb.add_format({'bold': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFF2CC', 'text_wrap': True})
    fmt_body = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})

    list_kelas_sorted = df['Kelas Lomba'].unique()
    for kelas in list_kelas_sorted:
        df_sub = df[df['Kelas Lomba'] == kelas][cols_final]
        sheet_name = str(kelas)[:30].replace("/", "-").replace(":", "").replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        ws = wb.add_worksheet(sheet_name)
        ws.merge_range(0, 0, 0, len(cols_final)-1, kelas.upper(), fmt_title)
        for col_num, col_name in enumerate(cols_final):
            ws.write(1, col_num, col_name, fmt_header)
        data_rows = df_sub.values.tolist()
        for row_idx, row_data in enumerate(data_rows):
            for col_idx, cell_value in enumerate(row_data):
                ws.write(row_idx + 2, col_idx, cell_value, fmt_body)
        for i, col_name in enumerate(cols_final):
            max_len = len(str(col_name))
            for val in df_sub[col_name]:
                if len(str(val)) > max_len: max_len = len(str(val))
            ws.set_column(i, i, max_len + 3)

    workbook.close()
    return output.getvalue()

# --- LOGIKA KELAS ---
def tentukan_kelas(tipe_show, ras_full, status, umur_cat):
    ras_kategori = ras_full
    if "Other Purebred" in ras_full:
        ras_kategori = "Other Purebred"
    if ras_kategori in ["Household Pet (Mix)", "Domestik"]:
        return f"{ras_kategori} - {umur_cat}"
    if "Tipe 1" in tipe_show:
        return f"{status} - {umur_cat}"
    elif "Tipe 2" in tipe_show:
        return f"{ras_kategori} - {umur_cat}"
    elif "Tipe 3" in tipe_show:
        return f"{ras_kategori} {status} - {umur_cat}"
    return "Umum"

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.header("⚙️ Konfigurasi Show")
    tipe_show = st.radio("Jenis Show:", ["Tipe 1: Simple (Ped vs Non-Ped)", "Tipe 2: Breed Base (Per Ras)", "Tipe 3: Complex (Breed + Status)"])
    st.divider()
    st.write("📂 **Admin Import**")
    uploaded_file = st.file_uploader("Upload Data Lama", type=["xlsx", "csv"])
    if uploaded_file and st.button("Gabung Data"):
        try:
            if uploaded_file.name.endswith('.csv'): df_in = pd.read_csv(uploaded_file)
            else: df_in = pd.read_excel(uploaded_file)
            add_data(df_in)
            st.success("Data berhasil diimport!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- UI UTAMA ---
st.title("Smart Groomer Indonesia")
st.subheader("🏆 Sistem Registrasi Catshow")
st.caption(f"Mode Aktif: {tipe_show}")

tab1, tab2 = st.tabs(["📝 Pendaftaran Baru", "🛠️ Database & Tools"])

# === TAB 1: FORM INPUT ===
with tab1:
    col_form_main, _ = st.columns([1, 0.1])
    with col_form_main:
        pesan_container = st.empty()
        kunci = str(st.session_state['form_key'])

        owner = st.text_input("Nama Pemilik", key=f"owner_{kunci}")
        hp = st.text_input("No HP / WA", key=f"hp_{kunci}")
        st.divider()
        cat_name = st.text_input("Nama Kucing", key=f"cat_{kunci}")
        
        c_warna, c_sex = st.columns([1.5, 1])
        with c_warna:
            warna = st.text_input("Warna / Pola", key=f"warna_{kunci}", placeholder="e.g. Red Tabby")
        with c_sex:
            sex = st.radio("Jenis Kelamin", ["Jantan", "Betina"], horizontal=True, key=f"sex_{kunci}")

        list_ras_utama = [
            "Persian", "Maine Coon", "British Shorthair (BSH)", 
            "Bengal", "Other Purebred (Ras Lain)",
            "Household Pet (Mix)", "Domestik"
        ]
        ras_pilih_utama = st.selectbox("Ras Kucing", list_ras_utama, key=f"ras_{kunci}")
        
        ras_final = ras_pilih_utama 
        if ras_pilih_utama == "Other Purebred (Ras Lain)":
            list_minoritas = ["- (Kosongkan)", "Ragdoll", "Sphynx", "Scottish Fold", "Munchkin", "Abyssinian", "Russian Blue", "Lainnya (Ketik Sendiri)"]
            sub_ras = st.selectbox("Pilih Detail Ras Lain:", list_minoritas, key=f"sub_ras_{kunci}")
            if sub_ras == "Lainnya (Ketik Sendiri)":
                custom_ras = st.text_input("Ketik Nama Ras:", key=f"custom_ras_{kunci}")
                if custom_ras: ras_final = f"Other Purebred ({custom_ras})"
            elif sub_ras != "- (Kosongkan)":
                ras_final = f"Other Purebred ({sub_ras})"
        
        is_mix = ras_final in ["Household Pet (Mix)", "Domestik"]
        is_tipe_2 = "Tipe 2" in tipe_show
        
        if is_mix:
            status_pilih = "Pet Class" 
            st.info(f"ℹ️ Kategori Pet Class.")
        elif is_tipe_2:
            status_pilih = "-"
            st.info("ℹ️ Status digabung (One Breed One Class).")
        else:
            status_pilih = st.radio("Status Sertifikat?", ["Pedigree", "Non-Pedigree"], horizontal=True, key=f"status_{kunci}")
            
        umur_pilih = st.radio("Kategori Umur?", ["Kitten", "Adult"], horizontal=True, key=f"umur_{kunci}")
        st.write("")
        
        if st.button("Daftarkan Peserta 🚀", type="primary"):
            if not owner or not cat_name or not warna:
                pesan_container.error("⚠️ Data belum lengkap!")
            else:
                kelas_final = tentukan_kelas(tipe_show, ras_final, status_pilih, umur_pilih)
                data_baru = pd.DataFrame([{
                    "Nama Pemilik": owner, "No HP": hp, "Nama Kucing": cat_name,
                    "Jenis Kelamin": sex,
                    "Ras": ras_final, "Warna": warna, "Status": status_pilih,
                    "Kategori Umur": umur_pilih, "Kelas Lomba": kelas_final
                }])
                add_data(data_baru)
                pesan_container.success(f"✅ {cat_name} ({sex}) terdaftar!")
                reset_form()
                st.rerun()

# === TAB 2: DATABASE & TOOLS ===
with tab2:
    df = load_data()
    
    if df.empty:
        st.info("Belum ada data peserta.")
    else:
        st.dataframe(df, use_container_width=True, height=300)
        
        st.subheader("🖨️ Cetak & Download")
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            # EXCEL KATALOG
            excel_data = to_excel_styled(df, tipe_show)
            st.download_button(
                label="📄 Katalog (Excel)",
                data=excel_data,
                file_name='Katalog_Catshow.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
            
        with col_dl2:
            # NOMOR URUT PDF
            # Pakai Checkbox biar PDF tidak digenerate terus-menerus
            if st.checkbox("🖨️ Buka Menu Cetak Label"):
                with st.spinner("Menyiapkan Label PDF..."): 
                    pdf_data = generate_number_tags(df, tipe_show)
                
                st.download_button(
                    label="⬇️ Download Label PDF",
                    data=pdf_data,
                    file_name='Label_Nomor.pdf',
                    mime='application/pdf',
                    use_container_width=True
                )

        with col_dl3:
            # BACKUP CSV
            csv_backup = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Backup (CSV)",
                data=csv_backup,
                file_name='Backup_Data_Catshow.csv',
                mime='text/csv',
                key='download-csv-tab2',
                use_container_width=True
            )
            
        st.divider()
        st.subheader("🛠️ Edit / Hapus Data")
        
        pilihan_edit = st.selectbox(
            "🔍 Pilih Peserta:",
            options=df.index,
            format_func=lambda x: f"{df.loc[x, 'Nama Kucing']} ({df.loc[x, 'Ras']}) | {df.loc[x, 'Nama Pemilik']}"
        )
        
        if pilihan_edit is not None:
            row_data = df.loc[pilihan_edit]
            with st.expander(f"Edit: {row_data['Nama Kucing']}", expanded=True):
                with st.form(key="edit_form"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        e_owner = st.text_input("Nama Pemilik", value=row_data['Nama Pemilik'])
                        e_hp = st.text_input("No HP", value=row_data['No HP'])
                        e_cat = st.text_input("Nama Kucing", value=row_data['Nama Kucing'])
                        e_sex = st.selectbox("Jenis Kelamin", ["Jantan", "Betina"], index=0 if row_data['Jenis Kelamin']=="Jantan" else 1)
                    with col_e2:
                        e_ras = st.text_input("Ras", value=row_data['Ras'])
                        e_warna = st.text_input("Warna", value=row_data['Warna'])
                        e_status = st.selectbox("Status", ["Pedigree", "Non-Pedigree", "Pet Class", "-"], index=["Pedigree", "Non-Pedigree", "Pet Class", "-"].index(row_data['Status']) if row_data['Status'] in ["Pedigree", "Non-Pedigree", "Pet Class", "-"] else 0)
                        e_umur = st.selectbox("Umur", ["Kitten", "Adult"], index=0 if row_data['Kategori Umur']=="Kitten" else 1)
                    
                    st.caption("⚠️ Kelas akan update otomatis.")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1: update_submitted = st.form_submit_button("💾 Simpan", type="primary", use_container_width=True)
                    with col_btn2: delete_submitted = st.form_submit_button("🗑️ Hapus", type="secondary", use_container_width=True)
                
                if update_submitted:
                    kelas_baru = tentukan_kelas(tipe_show, e_ras, e_status, e_umur)
                    df.loc[pilihan_edit] = [e_owner, e_hp, e_cat, e_sex, e_ras, e_warna, e_status, e_umur, kelas_baru]
                    save_overwrite(df)
                    st.success("Updated!")
                    st.rerun()

                if delete_submitted:
                    df = df.drop(index=pilihan_edit)
                    save_overwrite(df)
                    st.rerun()
                    
        st.divider()
        with st.expander("Danger Zone"):
            if st.button("🔴 RESET DATABASE"):
                if os.path.exists(FILE_DATABASE):
                    os.remove(FILE_DATABASE)
                    st.rerun()

# --- FOOTER ---
st.markdown("""
<style>
.footer {
    position: fixed; left: 0; bottom: 0; width: 100%;
    background-color: #0E1117; color: #FAFAFA;
    text-align: center; padding: 10px; border-top: 1px solid #333;
    font-size: 12px; z-index: 1000;
}
</style>
<div class="footer">
    <p>© 2026 <b>Smart Groomer Indonesia</b> | System & Website by Arif Dimas</b></p>
</div>
""", unsafe_allow_html=True)
