import streamlit as st
import pandas as pd
import gspread
import json
import re
from datetime import datetime

st.set_page_config(page_title="Báo Cáo Tương Tác KH - TPTS", layout="wide", page_icon="📈")

# ==========================================
# CẤU HÌNH THÔNG TIN & KẾT NỐI GOOGLE SHEETS
# ==========================================
NHAN_VIEN = "Trần Hữu Khiêm"
MA_NV = "NV03016"
NGANH_HANG = "TPTS"

# Tên chính xác của file Google Sheets
SHEET_NAME = "BC DATA TUONG TAC_TRAN HUU KHIEM 2026"

# Khuyến nghị: Copy link URL của file trên thanh địa chỉ trình duyệt và dán vào giữa dấu ngoặc kép bên dưới.
# (Nếu để trống "", ứng dụng sẽ tự động tìm theo SHEET_NAME ở trên)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1vNoVVTxQaNwfHEZibmCvVLa5Hcpvm1gsqyCwWgXsMgo/edit?gid=307870466#gid=307870466"

EXPECTED_COLUMNS = [
    "Ngày", "STT", "Tên khách hàng", "Nguồn", "Người liên hệ",
    "Số điện thoại", "Doanh thu ước tính (VNĐ)", "Trạng thái",
    "Ghi chú / Hẹn tiếp theo.", "Sản phẩm quan tâm"
]

DANH_SACH_NGUON = ["Sếp chuyển", "Hotline", "Zalo", "Facebook", "Giới thiệu", "Tự tìm", "Khác"]
DANH_SACH_TRANG_THAI = [
    "Chưa liên hệ được", "Chưa xin được số ĐT", "Đã liên hệ", "Đã tư vấn",
    "Đã gửi báo giá", "Chờ khách phản hồi", "Khách phản hồi", "Khách đã chốt",
    "Khách đã ký hợp đồng", "Chăm sóc lại lần 2", "Chăm sóc lại lần 3"
]

@st.cache_resource(ttl=300)
def get_gspread_client():
    credentials_dict = json.loads(st.secrets["GCP_CREDENTIALS_JSON"])
    return gspread.service_account_from_dict(credentials_dict)

def open_spreadsheet():
    gc = get_gspread_client()
    if SHEET_URL.strip():
        return gc.open_by_url(SHEET_URL.strip())
    return gc.open(SHEET_NAME)

def parse_vnd(val):
    digits = re.sub(r"[^\d]", "", str(val))
    return int(digits) if digits else 0

def load_worksheet_data(worksheet):
    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    rows = []
    for row in all_values[1:]:
        if not any(cell.strip() for cell in row):
            continue
        padded = (row + [""] * len(EXPECTED_COLUMNS))[:len(EXPECTED_COLUMNS)]
        rows.append(padded)

    return pd.DataFrame(rows, columns=EXPECTED_COLUMNS)

# ==========================================
# KẾT NỐI & CHỌN TAB THÁNG TRÊN SIDEBAR
# ==========================================
try:
    sh = open_spreadsheet()
    sheet_titles = [ws.title for ws in sh.worksheets()]
except Exception as e:
    st.error(
        f"Lỗi kết nối tới file '{SHEET_NAME}'. "
        f"Vui lòng kiểm tra quyền chia sẻ (Editor) cho email Service Account hoặc dán trực tiếp link vào biến SHEET_URL.\nChi tiết: {e}"
    )
    st.stop()

selected_tab = st.sidebar.selectbox(
    "📅 Chọn Sheet / Tháng báo cáo",
    sheet_titles,
    index=len(sheet_titles) - 1
)
if st.sidebar.button("🔄 Tải lại dữ liệu mới nhất"):
    st.rerun()

worksheet = sh.worksheet(selected_tab)
df = load_worksheet_data(worksheet)

st.title("📈 DASHBOARD PHÂN TÍCH KHÁCH HÀNG & HIỆU QUẢ BÁN HÀNG")
st.caption(f"Kỳ báo cáo: {selected_tab}/2026 | Nhân viên: {NHAN_VIEN} | Mã NV: {MA_NV} | Ngành hàng: {NGANH_HANG}")
st.divider()

if "save_msg" in st.session_state:
    st.success(st.session_state.pop("save_msg"))

tab1, tab2 = st.tabs(["📊 Dashboard Phân Tích", "📝 Nhập Báo Cáo Hàng Ngày"])

# --- TAB 1: DASHBOARD ---
with tab1:
    if not df.empty:
        tong_kh = len(df)
        da_lien_he = len(df[~df["Trạng thái"].isin(["Chưa liên hệ được", "Chưa xin được số ĐT", ""])])
        da_gui_bao_gia = len(df[df["Trạng thái"].isin([
            "Đã gửi báo giá", "Chờ khách phản hồi", "Khách phản hồi",
            "Khách đã chốt", "Khách đã ký hợp đồng", "Chăm sóc lại lần 2", "Chăm sóc lại lần 3"
        ])])
        khach_da_chot = len(df[df["Trạng thái"].isin(["Khách đã chốt", "Khách đã ký hợp đồng"])])

        df_calc = df.copy()
        df_calc["DT_So"] = df_calc["Doanh thu ước tính (VNĐ)"].apply(parse_vnd)
        doanh_thu_chot = df_calc[df_calc["Trạng thái"].isin(["Khách đã ký hợp đồng", "Khách đã chốt"])]["DT_So"].sum()
        doanh_thu_uoc_tinh = df_calc["DT_So"].sum()

        st.subheader(f"Bảng Chỉ Số Nhanh ({selected_tab})")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Tổng Khách", tong_kh)
        col2.metric("Đã Liên Hệ", da_lien_he)
        col3.metric("Đã Gửi Báo Giá", da_gui_bao_gia)
        col4.metric("Đã Chốt / Ký HĐ", khach_da_chot)
        col5.metric("DT Đã Chốt (VNĐ)", f"{doanh_thu_chot:,.0f}")
        st.caption(f"Tổng doanh thu ước tính toàn phễu trong {selected_tab}: **{doanh_thu_uoc_tinh:,.0f} VNĐ**")

        st.divider()
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.subheader("Đánh Giá Nguồn Lead")
            source_counts = df["Nguồn"].value_counts().reindex(DANH_SACH_NGUON, fill_value=0)
            st.bar_chart(source_counts)
        with c_chart2:
            st.subheader("Phân Bổ Trạng Thái Khách Hàng")
            status_counts = df["Trạng thái"].value_counts().reindex(DANH_SACH_TRANG_THAI, fill_value=0)
            st.bar_chart(status_counts)
    else:
        st.info(f"Sheet '{selected_tab}' hiện chưa có dữ liệu. Hãy nhập báo cáo đầu tiên ở tab bên cạnh!")

# --- TAB 2: NHẬP BÁO CÁO MỚI ---
with tab2:
    st.subheader(f"Ghi Nhận Tương Tác Khách Hàng Mới vào '{selected_tab}'")
    with st.form("daily_report_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            ngay = st.date_input("Ngày báo cáo", datetime.now())
            ten_kh = st.text_input("Tên khách hàng", placeholder="VD: MN Hoa Cúc")
            nguoi_lh = st.text_input("Người liên hệ", placeholder="VD: C Hương")
        with c2:
            sdt = st.text_input("Số điện thoại", placeholder="VD: 0901234567")
            nguon = st.selectbox("Nguồn lead", DANH_SACH_NGUON)
            san_pham = st.text_input("Sản phẩm quan tâm", placeholder="VD: Toàn bộ sản phẩm, Thịt, Rau...")
        with c3:
            doanh_thu_est = st.number_input("Doanh thu ước tính (VNĐ)", min_value=0, step=1000000)
            trang_thai = st.selectbox("Trạng thái hiện tại", DANH_SACH_TRANG_THAI)
            ghi_chu = st.text_area("Ghi chú / Hẹn tiếp theo", placeholder="VD: Đã gửi HSNL, theo dõi thêm")

        submit = st.form_submit_button(f"Lưu vào sheet '{selected_tab}' 🚀")

        if submit:
            if not ten_kh.strip():
                st.error("Vui lòng điền Tên khách hàng!")
            else:
                stt_nums = pd.to_numeric(df["STT"], errors="coerce").dropna()
                stt = int(stt_nums.max()) + 1 if not stt_nums.empty else 1

                sdt_clean = sdt.strip()
                sdt_to_save = f"'{sdt_clean}" if sdt_clean.startswith("0") else sdt_clean

                new_row = [
                    ngay.strftime("%Y-%m-%d"),
                    stt,
                    ten_kh.strip(),
                    nguon,
                    nguoi_lh.strip(),
                    sdt_to_save,
                    doanh_thu_est,
                    trang_thai,
                    ghi_chu.strip(),
                    san_pham.strip()
                ]
                worksheet.append_row(new_row, value_input_option="USER_ENTERED")
                st.session_state["save_msg"] = f"✅ Đã lưu '{ten_kh.strip()}' (STT: {stt}) vào tab '{selected_tab}'!"
                st.rerun()

    st.divider()
    st.subheader(f"Dữ Liệu Hiện Có Tại '{selected_tab}' ({len(df)} khách hàng)")
    st.dataframe(df, use_container_width=True)
