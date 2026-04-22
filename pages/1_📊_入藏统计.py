import streamlit as st
import pandas as pd
import io
import os

# --- 1. 固定配置 ---
LOCATION_TO_DEPT = {
    '借阅五区:1': '图书借阅部', '借阅三区:1': '图书借阅部', '借阅二区:1': '图书借阅部',
    '借阅一区:1': '图书借阅部', '西安海关分馆:1': '图书借阅部', '三立堂:1': '图书借阅部',
    '中图法三库:1': '图书借阅部','中图法二库:1': '图书借阅部',
    '保存本室:1': '典藏报刊部',
    '长安路儿童:1': '少儿部', '西大街儿童:1': '少儿部', '西大街少年:1': '少儿部',
    '长安路少年:1': '少儿部', '西大街绘本:1': '少儿部',
    '地方文献区:1': '地方文献部', '周秦汉唐区:1': '地方文献部', '陕西作家区:1': '地方文献部',
    '陕版展示室:1': '地方文献部', '黄河专题文献区:1': '地方文献部', '柳青文学奖文献区:1': '地方文献部',
    '古籍阅览室:1': '历史文献部', '近代文献室:1': '历史文献部',
    '知识产权专题区:1': '参考咨询部', '港台文献区:1': '参考咨询部', '工具书区:1': '参考咨询部',
    '艺术设计区:1': '参考咨询部', '立法决策文献区:1': '参考咨询部',
    '图书馆学室:1': '学会',
    '高新外借:1': '高新馆区', '高新三层图书区:1': '高新馆区', '高新四层图书区:1': '高新馆区',
    '高新网借柜:1': '高新馆区', '高新外借室:1': '高新馆区', '高新城市书房:1': '高新馆区',
    '高新中文图书区:1': '高新馆区', '高新绘本区:1': '高新馆区', '高新儿童区:1': '高新馆区',
    '高新少年区:1': '高新馆区', '高新中厅图书区:1': '高新馆区', '高新中转库:1': '高新馆区',
    '视听资料区:1': '数字资源部', '数字资源区:1': '数字资源部'
}

DEPT_ORDER = [
    '图书借阅部', '典藏报刊部', '少儿部', '地方文献部',
    '历史文献部', '参考咨询部', '学会', '高新馆区', '数字资源部'
]

# --- 2. 网页设置 ---
st.set_page_config(page_title="图书入藏统计工具", layout="wide")
st.title("📚 图书部室入藏数据统计 (内网版)")
st.markdown("上传《个别登记账》，未映射的分区也会自动统计。")

# --- 3. 上传组件 ---
uploaded_file = st.file_uploader("点击或拖拽上传 Excel 文件", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # 1. 提取批号
        temp_df = pd.read_excel(uploaded_file, header=None, nrows=3)
        full_batch_info = str(temp_df.iloc[2, 0]).strip()
        batch_name = full_batch_info.replace("批号:", "").replace("批号：", "").strip()

        # 2. 读取数据
        df = pd.read_excel(uploaded_file, header=3, skipfooter=2)
        df['馆藏地点'] = df['馆藏地点'].astype(str).str.strip()
        df['ISBN号'] = df['ISBN号'].astype(str).str.strip()
        df['流通单册价'] = pd.to_numeric(df['流通单册价'], errors='coerce').fillna(0)
        df['所属部门'] = df['馆藏地点'].map(LOCATION_TO_DEPT)

        # 3. 统计：已归类部门
        mapped_df = df[df['所属部门'].notna()].copy()
        stats = mapped_df.groupby('所属部门').agg(
            入藏册数=('馆藏地点', 'count'),
            码洋=('流通单册价', 'sum')
        ).reset_index()

        # 补全固定顺序底表
        full_dept_df = pd.DataFrame({'所属部门': DEPT_ORDER})
        dept_summary = pd.merge(full_dept_df, stats, on='所属部门', how='left')

        # 4. 统计：未归类分区 (列出具体名称)
        unmapped_df = df[df['所属部门'].isna()].copy()
        if not unmapped_df.empty:
            unmapped_stats = unmapped_df.groupby('馆藏地点').agg(
                入藏册数=('馆藏地点', 'count'),
                码洋=('流通单册价', 'sum')
            ).reset_index()
            # 为了合并，将“馆藏地点”列名改为“所属部门”
            unmapped_stats.rename(columns={'馆藏地点': '所属部门'}, inplace=True)
        else:
            unmapped_stats = pd.DataFrame(columns=['所属部门', '入藏册数', '码洋'])

        # 5. 计算全局总计
        total_volumes = df.shape[0]
        total_price = df['流通单册价'].sum()
        total_isbn_count = df['ISBN号'].nunique()

        # --- 6. 构造最终组合表格 ---
        # 第一行：批号
        row_batch = pd.DataFrame([{'所属部门': full_batch_info, '入藏册数': None, '码洋': None}])

        # 最后两行：总计
        row_total_v = pd.DataFrame([{'所属部门': '总计图书册数', '入藏册数': total_volumes, '码洋': total_price}])
        row_total_s = pd.DataFrame([{'所属部门': '总计图书种数', '入藏册数': total_isbn_count, '码洋': None}])

        # 顺序：批号 -> 固定部门 -> 未匹配分区 -> 总计册数 -> 总计种数
        final_df = pd.concat([row_batch, dept_summary, unmapped_stats, row_total_v, row_total_s], ignore_index=True)

        # 7. 界面显示预览
        st.success(f"解析成功！当前批号：{batch_name}")
        if not unmapped_df.empty:
            st.warning(f"检测到 {len(unmapped_stats)} 个未定义的馆藏地点，已自动列在下方。")


        st.subheader("统计结果预览")
        # 格式化显示（仅预览用）

        view_df = final_df.copy()
        # 3. 【新增这一行】格式化入藏册数（设置为 0 位小数，即显示为整数）
        view_df['入藏册数'] = view_df['入藏册数'].apply(
            lambda x: f"{x:.0f}" if isinstance(x, (int, float)) and not pd.isna(x) else x)
        view_df['码洋'] = view_df['码洋'].apply(
            lambda x: f"{x:.2f}" if isinstance(x, (int, float)) and not pd.isna(x) else x)
        st.table(view_df.fillna(""))

        # 8. 生成并下载 Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, sheet_name='统计汇总', index=False)
            workbook = writer.book
            worksheet = writer.sheets['统计汇总']
            money_fmt = workbook.add_format({'num_format': '0.00'})
            # 设置列宽和格式
            worksheet.set_column('A:A', 35)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 15, money_fmt)

        st.download_button(
            label="📥 点击下载统计报表 (Excel)",
            data=output.getvalue(),
            file_name=f"统计结果汇总{batch_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"处理出错，请检查文件格式是否正确。报错信息: {e}")
