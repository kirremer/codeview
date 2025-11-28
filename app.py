import streamlit as st
import pandas as pd
from PIL import Image
import io

# --- 页面基础配置 ---
st.set_page_config(page_title="衣服投票", layout="wide")

# --- 初始化 Session State (内存存储) ---
# 这些数据存在内存里，只要网页不重启，数据就在
if 'images_data' not in st.session_state:
    st.session_state.images_data = [] # 存储上传的图片对象
if 'votes' not in st.session_state:
    st.session_state.votes = {}       # 存储票数
if 'voters' not in st.session_state:
    st.session_state.voters = []      # 存储已投票的人
if 'voting_open' not in st.session_state:
    st.session_state.voting_open = False # 控制是否开始投票

# --- 侧边栏：管理员控制台 ---
with st.sidebar:
    st.header("🔧 管理员面板")
    
    # 简单的密码保护，防止朋友误操作
    admin_mode = st.checkbox("我是发起人 (勾选上传图片)")
    
    if admin_mode:
        st.subheader("1. 上传衣服图片")
        uploaded_files = st.file_uploader(
            "选择图片 (支持多选)", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )
        
        # 处理上传
        if uploaded_files:
            # 只有当点击确认且当前没有图片时，才加载（避免重复追加）
            if st.button("确认加载这些图片"):
                st.session_state.images_data = [] # 清空旧图
                st.session_state.votes = {}       # 清空票数
                for uploaded_file in uploaded_files:
                    # 将上传的文件转为字节流存入内存
                    bytes_data = uploaded_file.getvalue()
                    name = uploaded_file.name
                    st.session_state.images_data.append({"name": name, "data": bytes_data})
                st.success(f"成功加载 {len(uploaded_files)} 张图片！")

        st.divider()
        st.subheader("2. 投票控制")
        
        # 开关投票
        if st.toggle("开启投票通道", value=st.session_state.voting_open):
            st.session_state.voting_open = True
        else:
            st.session_state.voting_open = False
            
        st.divider()
        st.subheader("3. 数据管理")
        st.write(f"当前总票数: {sum(st.session_state.votes.values())}")
        
        # 导出数据
        if st.button("生成 Excel 结果"):
            if not st.session_state.votes:
                st.warning("还没人投票")
            else:
                data = []
                for img_info in st.session_state.images_data:
                    name = img_info['name']
                    data.append({
                        "衣服": name,
                        "票数": st.session_state.votes.get(name, 0)
                    })
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下载结果 CSV", csv, "results.csv", "text/csv")
        
        if st.button("🔴 清空所有数据 (慎点)"):
            st.session_state.votes = {}
            st.session_state.voters = []
            st.session_state.images_data = []
            st.rerun()

# --- 主界面：用户投票区 ---
st.title("👔 衣服挑选投票")

# 检查是否有图片
if not st.session_state.images_data:
    st.info("👋 欢迎！管理员还没上传图片，请稍等...")
    st.stop()

# 检查投票通道是否开启
if not st.session_state.voting_open:
    st.warning("⚠️ 投票通道暂时关闭，请等待管理员开启。")
    # 即使关闭，管理员也可以预览图片
    if not admin_mode:
        st.stop()

# 投票逻辑
if not admin_mode:
    st.caption("请勾选你喜欢的衣服，最后点击提交。")
    voter_name = st.text_input("你的名字", placeholder="输入名字后才能提交")

with st.form("vote_form"):
    # 图片网格布局
    cols = st.columns(3) # 一行3张图
    selected_imgs = []
    
    for idx, img_info in enumerate(st.session_state.images_data):
        col = cols[idx % 3]
        with col:
            # 从内存显示图片
            image = Image.open(io.BytesIO(img_info['data']))
            st.image(image, use_column_width=True)
            
            # 显示票数（可选）
            current_count = st.session_state.votes.get(img_info['name'], 0)
            st.markdown(f"**当前票数: {current_count}**")
            
            # 只有非管理员模式且通道开启才显示勾选框
            if not admin_mode and st.session_state.voting_open:
                if st.checkbox(f"喜欢这件 (#{idx+1})", key=img_info['name']):
                    selected_imgs.append(img_info['name'])
    
    st.divider()
    
    # 提交按钮
    if not admin_mode and st.session_state.voting_open:
        submitted = st.form_submit_button("✅ 提交我的选择", type="primary")
        if submitted:
            if not voter_name:
                st.error("❌ 必须要写名字！")
            elif voter_name in st.session_state.voters:
                st.warning("你已经投过啦！")
            elif not selected_imgs:
                st.warning("一件都没选吗？")
            else:
                # 记票
                for name in selected_imgs:
                    st.session_state.votes[name] = st.session_state.votes.get(name, 0) + 1
                st.session_state.voters.append(voter_name)
                st.balloons() # 撒花特效
                st.success("投票成功！")
                st.rerun()