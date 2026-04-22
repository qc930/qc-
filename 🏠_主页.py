import streamlit as st

st.set_page_config(page_title="图书馆工具箱", page_icon="📚", layout="wide")

st.title("📚 图书馆业务自动化工具箱")
st.markdown("""
欢迎使用图书馆自动化处理工具！请在左侧菜单选择对应的功能：

1.  **📊 入藏统计**：上传《个别登记账》，按部室统计册数、码洋和总种数。
2.  **🔍 图书对账**：上传《供货书单》、《个别登记账》、《退书清单》，自动比对差异。
""")