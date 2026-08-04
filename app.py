import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime

st.set_page_config(page_title="Báo Cáo Tương Tác KH - TPTS", layout="wide", page_icon="📈")

NHAN_VIEN = "Trần Hữu Khiêm"
MA_NV = "NV03016"
NGANH_HANG = "TPTS"
THANG_BC = "08/2026"

st.title(f"📈 DASHBOARD PHÂN TÍCH KHÁCH HÀNG & HIỆU QUẢ BÁN HÀNG")
st.caption(f"Tháng {THANG_BC} | Nhân viên: {NHAN_VIEN} | Mã NV: {MA_NV} | Ngành hàng: {NGANH_HANG}")
st.divider()

# ==========================================
# HÀM KẾT NỐI VÀ ĐỌC DỮ LIỆU TỪ GOOGLE SHEETS
# ==========================================
@st.cache_resource(ttl=60)
def get_gspread_client():
    credentials_dict = json.loads(st.secrets["GCP_CREDENTIALS_JSON"])
    gc = gspread.service_account_from_dict(credentials_dict)
    return gc

def get_data():
    try:
        gc = get_gspread_client()
        # Nếu đang dùng link URL thì thay lại dòng dưới thành gc.open_by_url("link_của_anh")
        sh = gc.open("https://docs.google.com/spreadsheets/d/1a03CxGHIOBICVKCJSUzdqJnUx7BxqiNfjez2Tvknhr4/edit?gid=0#gid=0") 
        worksheet = sh.sheet1
        records = worksheet.get_all_records()
        return pd.DataFrame(records), worksheet
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return pd.DataFrame(), None

df, worksheet = get_data()

DANH_SACH_NGUON = ["Sếp chuyển", "Hotline", "Zalo", "Facebook", "Giới thiệu", "Tự tìm", "Khác"]
DANH_SACH_TRANG_THAI = [
    "Chưa liên hệ được", "Chưa xin được số ĐT", "Đã liên hệ", "Đã tư vấn", 
    "Đã gửi báo giá", "Chờ khách phản hồi", "Khách phản hồi", "Khách đã chốt", 
    "Khách đã ký hợp đồng", "Chăm sóc lại lần 2", "Chăm sóc lại lần 3"
]

tab1, tab2 = st.tabs(["📊 Dashboard Phân Tích", "📝 Báo Cáo Khách Hàng Hàng Ngày"])

# --- TAB 1: DASHBOARD ---
with tab1:
    if not df.empty:
        tong_kh = len(df)
        da_lien_he = len(df[~df['Trạng thái'].isin(["Chưa liên hệ được", "Chưa xin được số ĐT"])])
        da_gui_bao_gia = len(df[df['Trạng thái'].isin([
            "Đã gửi báo giá", "Chờ khách phản hồi", "Khách phản hồi", 
            "Khách đã chốt", "Khách đã ký hợp đồng", "Chăm sóc lại lần 2", "Chăm sóc lại lần 3"
        ])])
        khach_da_chot = len(df[df['Trạng thái'].isin([
            "Khách đã chốt", "Khách đã ký hợp đồng", "Chăm sóc lại lần 2", "Chăm sóc lại lần 3"
        ])])
        
        df['Doanh thu ước tính (VNĐ)'] = pd.to_numeric(df['Doanh thu ước tính (VNĐ)'].replace('[\$,]', '', regex=True), errors='coerce').fillna(0)
        doanh_thu = df[df['Trạng thái'].isin(["Khách đã ký hợp đồng", "Khách đã chốt"])]['Doanh thu ước tính (VNĐ)'].sum()

        st.subheader("Bảng Chỉ Số Nhanh (Luỹ kế)")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Tổng Khách", tong_kh)
        col2.metric("Đã Liên Hệ", da_lien_he)
        col3.metric("Đã Gửi Báo Giá", da_gui_bao_gia)
        col4.metric("Khách Đã Chốt", khach_da_chot)
        col5.metric("Doanh Thu (VNĐ)", f"{doanh_thu:,.0f}")

        st.divider()
        st.subheader("Đánh Giá Nguồn Lead")
        source_counts = df['Nguồn'].value_counts().reindex(DANH_SACH_NGUON, fill_value=0)
        st.bar_chart(source_counts)
    else:
        st.info("Chưa có dữ liệu. Vui lòng nhập báo cáo đầu tiên ở tab bên cạnh!")

# --- TAB 2: NHẬP BÁO CÁO MỚI ---
with tab2:
    st.subheader("Ghi Nhận Tương Tác Khách Hàng Mới")
    with st.form("daily_report_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        
        with c1:
            ngay = st.date_input("Ngày báo cáo", datetime.now())
            ten_kh = st.text_input("Tên khách hàng", placeholder="VD: Mầm non Hoa Cúc")
            nguoi_lh = st.text_input("Người liên hệ")
            
        with c2:
            sdt = st.text_input("Số điện thoại")
            nguon = st.selectbox("Nguồn lead", DANH_SACH_NGUON)
            san_pham = st.text_input("Sản phẩm quan tâm", placeholder="VD: Thịt Heo, Rau Củ...")
            
        with c3:
            doanh_thu_est = st.number_input("Doanh thu ước tính (VNĐ)", min_value=0, step=1000000)
            trang_thai = st.selectbox("Trạng thái hiện tại", DANH_SACH_TRANG_THAI)
            ghi_chu = st.text_area("Ghi chú / Hẹn tiếp theo", placeholder="VD: Gửi mẫu ăn thử vào tuần sau")
            
        submit = st.form_submit_button("Đồng Bộ Thẳng Lên Google Sheets 🚀")
        
        if submit:
            if not ten_kh:
                st.error("Vui lòng điền Tên khách hàng!")
            elif worksheet is None:
                st.error("Không tìm thấy Google Sheets. Vui lòng kiểm tra lại!")
            else:
                # TỰ ĐỘNG TÍNH STT: Lấy tổng số dòng hiện tại cộng thêm 1
                stt = len(df) + 1 if not df.empty else 1
                
                # CẬP NHẬT MẢNG DỮ LIỆU: Chèn stt vào ngay sau ngày
                new_row = [
                    ngay.strftime("%Y-%m-%d"), stt, ten_kh, nguon, nguoi_lh, sdt, 
                    doanh_thu_est, trang_thai, ghi_chu, san_pham
                ]
                worksheet.append_row(new_row)
                st.success(f"✅ Đã chốt và lưu báo cáo của {ten_kh} (STT: {stt}) lên Google Sheets!")
                st.form_submit_button("🔁 Bấm vào đây để làm mới Dashboard")

    st.divider()
    st.subheader("Dữ Liệu Tổng Hợp (Lấy trực tiếp từ Google Sheets)")
    st.dataframe(df, use_container_width=True)
