import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
import unicodedata
import pytz
import json

# 1. CẤU HÌNH KẾT NỐI (Dùng st.secrets theo chuẩn Streamlit)
def get_connection():
    # Load credentials từ Streamlit Secrets
    creds_dict = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(creds_dict)
    return gc

# Khởi tạo client
client = get_connection()
sheet = client.open_by_key("1Yb4hroqlW8mIx0X5wWHa8ggrIUZK3z0Wbk4JavBaavA").worksheet("data tvn mma")

# Các hàm hỗ trợ
def remove_accents(input_str):
    if not isinstance(input_str, str): input_str = str(input_str)
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

# 2. XÁC THỰC NGƯỜI DÙNG
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
    st.title("Chào mừng đến với hệ thống!")
    user_choice = st.selectbox("Chọn tên của bạn:", ["Phú", "Thắng", "Nguyên", "Thoại"])
    if st.button("Xác nhận"):
        st.session_state.current_user = user_choice
        st.rerun()
    st.stop()

# 3. LẤY VÀ XỬ LÝ DỮ LIỆU
all_data = sheet.get_all_values()

if not all_data or len(all_data) == 0:
    st.error("Sheet không có dữ liệu!")
    st.stop()
else:
    header = all_data[0]
    df = pd.DataFrame(all_data[1:], columns=header)

# Đảm bảo các cột cần thiết
required_columns = ["STT", "Chủ đề", "Trạng thái", "Người làm", "Link src", "Link final", "Deadline", "Note", "Lịch sử"]
for col in required_columns:
    if col not in df.columns:
        df[col] = ""

df['search_key'] = (df['Chủ đề'].fillna('').astype(str) + " " + df['Người làm'].fillna('').astype(str)).apply(remove_accents)

# 4. GIAO DIỆN & TƯƠNG TÁC
st.sidebar.info(f"User: **{st.session_state.current_user}**")
if st.sidebar.button("Đăng xuất"):
    st.session_state.current_user = None
    st.rerun()

st.dataframe(df, use_container_width=True)

# (Tiếp tục các phần Form thêm/sửa/xóa của bạn ở đây...)

# 4. FORM THÊM DỮ LIỆU
st.subheader("📝 Thêm nội dung mới")
status_options = ["Chưa", "Đang làm", "Rồi", "Đã xóa"] 
person_options = ["Phú", "Thắng", "Nguyên", "Thoại"]

# Đảm bảo danh sách cột của bạn trong code khớp với cột trên Sheet (9 cột)
columns = ["STT", "Chủ đề", "Trạng thái", "Người làm", "Link src", "Link final", "Deadline", "Note", "Lịch sử"]

with st.form("add_data_form"):
    col1, col2 = st.columns(2)
    input_fields = {
        "Chủ đề": st.text_input("Chủ đề:"),
        "Trạng thái": st.selectbox("Trạng thái:", status_options),
        "Người làm": st.selectbox("Người làm:", person_options),
        "Link src": st.text_input("Link src:"),
        "Link final": st.text_input("Link final:"),
        "Deadline": st.text_input("Deadline:"),
        "Note": st.text_input("Note:")
    }
    
    if st.form_submit_button("Lưu dữ liệu"):
        vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        today = datetime.now(vn_timezone).strftime("%d/%m %H:%M")
        
        # Sửa dòng này trong khối if st.form_submit_button:
        row_data = [
            input_fields["Chủ đề"],
            input_fields["Trạng thái"],
            input_fields["Người làm"],
            input_fields["Link src"],
            input_fields["Link final"],
            input_fields["Deadline"],
            input_fields["Note"],
            f"Tạo lúc: {today}",
            f"{today} - {st.session_state.current_user} tạo" # Phải dùng đúng tên này
        ]
        
        sheet.append_row(row_data)
        st.success("Đã lưu thành công!")
        st.rerun()

# 5. SỬA / XÓA AN TOÀN (Đã cập nhật ghi Log)
st.subheader("⚙️ Thao tác dữ liệu")
search_query = st.text_input("Tìm nhanh:", placeholder="Gõ tên task hoặc người làm...")

if search_query:
    query_parts = remove_accents(search_query).split()
    search_df = df
    for part in query_parts:
        search_df = search_df[search_df['search_key'].str.contains(part, na=False)]
    
    if not search_df.empty:
        for index, row in search_df.iterrows():
            actual_index = row.name 
            
            if row['Trạng thái'] == "Đã xóa":
                if st.button(f"🔄 Khôi phục: {row['Chủ đề']}", key=f"undo_{actual_index}"):
                    # Ghi log khi khôi phục
                    log = f"{datetime.now().strftime('%d/%m %H:%M')} - {st.session_state.current_user} khôi phục"
                    sheet.update_cell(actual_index + 2, columns.index("Trạng thái") + 1, "Chưa")
                    sheet.update_cell(actual_index + 2, columns.index("Lịch sử") + 1, log)
                    st.success("Đã khôi phục thành công!")
                    st.rerun()
            else:
                with st.expander(f"Task: {row['Chủ đề']} - Người làm: {row['Người làm']}"):
                    # Form Chỉnh sửa
                    with st.form(key=f"edit_{actual_index}"):
                        new_chu_de = st.text_input("Chủ đề", value=row['Chủ đề'])
                        new_trang_thai = st.selectbox("Trạng thái", [s for s in status_options if s != "Đã xóa"], 
                                                      index=[s for s in status_options if s != "Đã xóa"].index(row['Trạng thái']))
                        
                        if st.form_submit_button("Lưu thay đổi"):
                            # Ghi log khi sửa
                            log = f"{datetime.now().strftime('%d/%m %H:%M')} - {st.session_state.current_user} sửa"
                            sheet.update_cell(actual_index + 2, columns.index("Chủ đề") + 1, new_chu_de)
                            sheet.update_cell(actual_index + 2, columns.index("Trạng thái") + 1, new_trang_thai)
                            sheet.update_cell(actual_index + 2, columns.index("Lịch sử") + 1, log)
                            st.success("Đã cập nhật!")
                            st.rerun()
                    
                    # Xác nhận 2 bước
                    with st.popover("🗑️ Xóa task này"):
                        st.write("Bạn chắc chắn muốn chuyển task này vào thùng rác?")
                        if st.button("Xác nhận xóa", key=f"del_{actual_index}"):
                            # Ghi log khi xóa
                            log = f"{datetime.now().strftime('%d/%m %H:%M')} - {st.session_state.current_user} xóa"
                            sheet.update_cell(actual_index + 2, columns.index("Trạng thái") + 1, "Đã xóa")
                            sheet.update_cell(actual_index + 2, columns.index("Lịch sử") + 1, log)
                            st.warning("Đã di chuyển vào thùng rác!")
                            st.rerun()
    else:
        st.warning("Không tìm thấy kết quả.")