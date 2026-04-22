
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="图书对账工具", layout="wide")

st.title("🔍 图书发货/验收/退书对账工具")

# --- 1. 列名要求说明 ---
with st.expander("📌 使用前请检查 Excel 列名要求", expanded=True):
    st.markdown("""
    1. **供货书单**：必须包含 `书号`、`书名`、`册数`、`码洋`。
    2. **个别登记账**：验收清单也行，建议个别登记账。
    3. **退书清单**：程序会自动查找包含 `ISBN`、`数量`、`总价/码洋` ）。
    """)


# --- 工具函数 ---
def clean_isbn(isbn):
    if pd.isna(isbn): return ""
    s = str(isbn).strip()
    if s.endswith('.0'): s = s[:-2]
    return s.replace('-', '').replace(' ', '')


def clean_num(x):
    if pd.isna(x): return 0.0
    try:
        return float(x)
    except:
        return 0.0


# --- 2. 文件上传区 ---
col1, col2, col3 = st.columns(3)
with col1:
    file_supply = st.file_uploader("1. 上传【供货书单】(必填)", type=["xlsx", "xls"])
with col2:
    file_accept = st.file_uploader("2. 上传【个别登记账】(必填)", type=["xlsx", "xls"])
with col3:
    file_return = st.file_uploader("3. 上传【退书清单】(可选)", type=["xlsx", "xls"])

if st.button("🚀 开始对账", type="primary"):
    if not file_supply or not file_accept:
        st.error("❌ 请至少上传【供货书单】和【个别登记账】。")
    else:
        try:
            # --- A. 提取个别登记账批号 (用于命名) ---
            temp_batch_df = pd.read_excel(file_accept, header=None, nrows=3)
            full_batch_str = str(temp_batch_df.iloc[2, 0]).strip()
            batch_name_val = full_batch_str.split(":")[-1].split("：")[-1].strip() if any(
                s in full_batch_str for s in [":", "："]) else full_batch_str
            if not batch_name_val or batch_name_val == "nan": batch_name_val = "未知批号"

            errors = []

            # --- B. 读取并检查【供货书单】 ---
            try:
                df_supply = pd.read_excel(file_supply, sheet_name='清单', header=0)
            except:
                df_supply = pd.read_excel(file_supply, header=0)

            for col in ['书号', '册数', '码洋']:
                if col not in df_supply.columns:
                    errors.append(f"【供货书单】缺少列: `{col}`")

            # --- C. 读取并检查【个别登记账】 (跳过最后两行) ---
            # header=3 表示第4行是表头，skipfooter=2 表示忽略最后两行
            df_accept = pd.read_excel(file_accept, header=3, skipfooter=2)
            for col in ['ISBN号', '数量', '流通单册价']:
                if col not in df_accept.columns:
                    errors.append(f"【个别登记账】缺少列: `{col}` (当前识别到表头在第4行，请检查文件)")

            # --- D. 读取并处理【退书清单】 (跳过最后两行) ---
            df_return = pd.DataFrame(columns=['clean_isbn', 'qty', 'total_price'])
            if file_return:
                # 尝试从第2行读取表头，并忽略最后两行
                df_ret_raw = pd.read_excel(file_return, header=1, skipfooter=2)

                # 如果没读到 ISBN 列，尝试从第1行读取表头，并忽略最后两行
                if not any(c in df_ret_raw.columns for c in ['序号.1', 'ISBN', '书号', 'ISBN号']):
                    df_ret_raw = pd.read_excel(file_return, header=0, skipfooter=2)

                ret_map = {
                    '序号.1': 'ISBN_REF', 'ISBN': 'ISBN_REF', 'ISBN号': 'ISBN_REF', '书号': 'ISBN_REF',
                    '序号.2': 'TITLE_REF', '名称': 'TITLE_REF', '书名': 'TITLE_REF', '题名': 'TITLE_REF',
                    '数量': 'QTY_REF', '册数': 'QTY_REF', '实发数': 'QTY_REF', '实发数量': 'QTY_REF',
                    '总价': 'PRICE_REF', '码洋': 'PRICE_REF', '总额': 'PRICE_REF', '码洋总计': 'PRICE_REF'
                }
                df_ret_raw.rename(columns=ret_map, inplace=True)

                if 'ISBN_REF' not in df_ret_raw.columns:
                    errors.append("【退书清单】无法识别 ISBN 列")
                if 'QTY_REF' not in df_ret_raw.columns:
                    errors.append("【退书清单】无法识别 数量 列")
                if 'PRICE_REF' not in df_ret_raw.columns:
                    errors.append("【退书清单】无法识别 金额 列")

                if not errors:
                    df_return['clean_isbn'] = df_ret_raw['ISBN_REF'].apply(clean_isbn)
                    df_return['qty'] = df_ret_raw['QTY_REF'].apply(clean_num)
                    df_return['total_price'] = df_ret_raw['PRICE_REF'].apply(clean_num)

            # --- E. 判定报错 ---
            if errors:
                for e in errors: st.error(e)
                st.stop()

            # --- F. 计算逻辑 ---
            with st.spinner("正在交叉对账中..."):
                df_supply['clean_isbn'] = df_supply['书号'].apply(clean_isbn)
                agg_supply = df_supply.groupby('clean_isbn').agg(s_qty=('册数', 'sum'),
                                                                 s_total=('码洋', 'sum')).reset_index()

                df_accept['clean_isbn'] = df_accept['ISBN号'].apply(clean_isbn)
                df_accept['total_price_calc'] = df_accept['数量'] * df_accept['流通单册价']
                agg_accept = df_accept.groupby('clean_isbn').agg(a_qty=('数量', 'sum'),
                                                                 a_total=('total_price_calc', 'sum')).reset_index()

                agg_return = df_return.groupby('clean_isbn').agg(r_qty=('qty', 'sum'),
                                                                 r_total=('total_price', 'sum')).reset_index()

                all_isbns = pd.concat(
                    [agg_supply['clean_isbn'], agg_accept['clean_isbn'], agg_return['clean_isbn']]).unique()
                df_merged = pd.DataFrame({'clean_isbn': [i for i in all_isbns if i]})
                df_merged = df_merged.merge(agg_supply, on='clean_isbn', how='left').merge(agg_accept, on='clean_isbn',
                                                                                           how='left').merge(agg_return,
                                                                                                             on='clean_isbn',
                                                                                                             how='left').fillna(
                    0)

                df_merged['实收+退回册数'] = df_merged['a_qty'] + df_merged['r_qty']
                df_merged['数量差异'] = df_merged['s_qty'] - df_merged['实收+退回册数']
                df_merged['实收+退回码洋'] = df_merged['a_total'] + df_merged['r_total']
                df_merged['金额差异'] = (df_merged['s_total'] - df_merged['实收+退回码洋']).round(2)


                def get_status(row):
                    if abs(row['金额差异']) < 0.1:
                        return "完全一致" if row['数量差异'] == 0 else "金额一致，数量差异"
                    return "未入库/未退货" if row['a_total'] == 0 and row['r_total'] == 0 else "差异"


                df_merged['对账结果'] = df_merged.apply(get_status, axis=1)

                df_final = df_merged.rename(columns={
                    'clean_isbn': 'ISBN', 's_qty': '供货册数', 's_total': '供货码洋',
                    'a_qty': '验收册数', 'a_total': '验收码洋', 'r_qty': '退货册数', 'r_total': '退货码洋'
                })

                st.success(f"✅ 对账完成！批号：{batch_name_val}")
                st.dataframe(df_final)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='结果汇总')

                st.download_button(
                    label=f"📥 下载：{batch_name_val}对账结果.xlsx",
                    data=output.getvalue(),
                    file_name=f"{batch_name_val}对账结果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"⚠️ 程序运行异常: {e}")
