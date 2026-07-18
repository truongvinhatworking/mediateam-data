import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import unicodedata
import pytz

# --- TRÊN ĐẦU FILE ---
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Logic xác thực
if st.session_state.current_user is None:
    st.title("Chào mừng đến với hệ thống!")
    st.subheader("⚠️ Mày là ai?")
    with st.form("login_form"):
        user_choice = st.selectbox("Chọn tên của bạn:", ["Phú", "Thắng", "Nguyên", "Thoại"])
        submit = st.form_submit_button("Xác nhận")
        if submit:
            st.session_state.current_user = user_choice
            st.rerun()
    st.stop() 

# --- PHẦN SIDEBAR BÊN DƯỚI (Dùng để hiển thị, KHÔNG ĐỂ CHỌN LẠI) ---
st.sidebar.subheader("👤 Vai trò hiện tại:")
# Hiển thị text thay vì selectbox, người dùng không thể đổi được nữa
st.sidebar.info(f"Đang làm việc với tư cách: **{st.session_state.current_user}**")

if st.sidebar.button("Đăng xuất (Chọn lại vai)"):
    st.session_state.current_user = None
    st.rerun()

st.sidebar.markdown("---")


# 1. CẤU HÌNH
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

def remove_accents(input_str):
    if not isinstance(input_str, str): input_str = str(input_str)
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

# 2. LẤY DỮ LIỆU
tab_name = "data tvn mma" 
sheet = client.open_by_key("1Yb4hroqlW8mIx0X5wWHa8ggrIUZK3z0Wbk4JavBaavA").worksheet(tab_name)

# Lấy tất cả dữ liệu thô
all_data = sheet.get_all_values()

if len(all_data) > 1:
    # Lấy hàng đầu tiên để làm header, nhưng lấy đúng số lượng cột của nó
    # Điều này tránh lỗi khi dữ liệu hàng dưới bị thừa cột
    data_rows = all_data[1:]
    
    # Ép tất cả các hàng về đúng số cột bằng với header bạn mong muốn (9 cột)
    # Chúng ta chỉ lấy 9 phần tử đầu tiên của mỗi hàng
    cleaned_data = [row[:9] for row in data_rows]
    
    header = ["STT", "Chủ đề", "Trạng thái", "Người làm", "Link src", "Link final", "Deadline", "Note", "Lịch sử"]
    df = pd.DataFrame(cleaned_data, columns=header)
else:
    df = pd.DataFrame(columns=["STT", "Chủ đề", "Trạng thái", "Người làm", "Link src", "Link final", "Deadline", "Note", "Lịch sử"])

# 3. BỘ LỌC (Sidebar)

st.sidebar.subheader("🔍 Bộ lọc nhanh")
show_deleted = st.sidebar.checkbox("Hiển thị cả các task đã xóa")

# Lọc theo Trạng thái (vẫn giữ logic tự động để linh hoạt)
unique_statuses = sorted([s for s in df['Trạng thái'].unique() if s])
status_filter = st.sidebar.multiselect("Lọc theo Trạng thái:", unique_statuses)

# Lọc theo Người làm (Cố định 4 người theo yêu cầu)
person_options = ["Phú", "Thắng", "Nguyên", "Thoại"]
person_filter = st.sidebar.multiselect("Lọc theo Người làm:", person_options)

# --- ÁP DỤNG BỘ LỌC VÀO BẢNG CHÍNH ---
filtered_df = df.copy()

# Lọc Trạng thái
if status_filter:
    filtered_df = filtered_df[filtered_df['Trạng thái'].isin(status_filter)]

# CẢI TIẾN: Lọc Người làm theo kiểu tìm kiếm chuỗi
if person_filter:
    # Tạo một điều kiện lọc: giữ lại những dòng có chứa ÍT NHẤT một trong các tên được chọn
    # Dùng regex=False để tìm chuỗi đơn giản, case=False để không phân biệt hoa thường
    condition = filtered_df['Người làm'].apply(lambda x: any(p.lower() in str(x).lower() for p in person_filter))
    filtered_df = filtered_df[condition]

# Loại bỏ "Đã xóa" nếu không bật checkbox
if not show_deleted:
    filtered_df = filtered_df[filtered_df['Trạng thái'] != "Đã xóa"]

st.dataframe(filtered_df, use_container_width=True)

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