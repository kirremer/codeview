import streamlit as st
import pandas as pd
from PIL import Image
import io

# --- 页面基础配置 ---
st.set_page_config(page_title="衣服投票", layout="wide")

# --- 核心修改：定义全局共享状态 ---
@st.cache_resource
class GlobalState:
    def __init__(self):
        self.images_data = []  # 公共图片数据
        self.votes = {}        # 公共投票数据
        self.voters = []       # 公共已投票名单
        self.voting_open = False # 公共开关状态

# 获取全局状态实例
state = GlobalState()

# --- 侧边栏：管理员控制台 ---
with st.sidebar:
    st.header("🔧 管理员面板")
    
    # 勾选开启管理员模式
    admin_mode = st.checkbox("我是发起人 (勾选上传图片)")
    
    if admin_mode:
        st.info("💡 提示：管理员模式下只能预览图片和管理数据，无法投票。如需投票，请取消勾选上面的框。")
        st.subheader("1. 上传衣服图片")
        uploaded_files = st.file_uploader(
            "选择图片 (支持多选)", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )
        
        # 上传逻辑
        if uploaded_files:
            if st.button("🔴 确认覆盖并发布图片"):
                # 清空旧数据
                state.images_data = []
                state.votes = {}
                state.voters = [] # 图片换了，投票人也重置
                
                # 处理新图片
                for uploaded_file in uploaded_files:
                    bytes_data = uploaded_file.getvalue()
                    name = uploaded_file.name
                    # 存入全局列表
                    state.images_data.append({"name": name, "data": bytes_data})
                    # 初始化这张图的票数为0
                    state.votes[name] = 0
                
                st.success(f"成功发布 {len(uploaded_files)} 张图片！朋友们现在刷新页面就能看到了。")

        st.divider()
        st.subheader("2. 投票控制")
        
        # 投票开关
        if st.checkbox("开启投票通道", value=state.voting_open):
            state.voting_open = True
        else:
            state.voting_open = False
            
        st.divider()
        st.subheader("3. 结果查看")
        total_votes = sum(state.votes.values())
        st.write(f"当前总票数: {total_votes}")
        st.write(f"参与人数: {len(state.voters)}")
        st.write(f"已投票名单: {', '.join(state.voters)}")
        
        # 导出结果
        if st.button("生成 Excel 结果"):
            if not state.votes:
                st.warning("暂无数据")
            else:
                data = []
                for img_info in state.images_data:
                    name = img_info['name']
                    data.append({
                        "衣服文件名": name,
                        "获得票数": state.votes.get(name, 0)
                    })
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下载结果 CSV", csv, "results.csv", "text/csv")
        
        # 紧急清空
        if st.button("❌ 清空所有数据"):
            state.images_data = []
            state.votes = {}
            state.voters = []
            st.rerun()

# --- 主界面：用户投票区 ---
st.title("👔 衣服挑选投票")

# 1. 检查是否有图片
if not state.images_data:
    st.info("👋 欢迎！发起人还没有上传图片，请稍等片刻...")
    if not admin_mode:
        st.stop() # 如果不是管理员，就停止往下渲染

# 2. 检查投票通道
if not state.voting_open:
    st.warning("⚠️ 投票通道暂时关闭，请等待管理员开启。")
    if not admin_mode:
        st.stop()

# 3. 用户输入区
if not admin_mode:
    st.write("👇 请勾选你喜欢的衣服，然后点击底部的提交按钮。")
    voter_name = st.text_input("请输入你的名字", placeholder="例如：Alex")

# --- 关键修复：根据模式选择不同的容器 ---
# 只有在非管理员（投票）模式下，才使用 st.form，这样管理员预览时就不会报 "Missing Submit Button" 的警告了
if not admin_mode:
    content_container = st.form("vote_form")
else:
    content_container = st.container()

# 4. 图片展示与表单
with content_container:
    # 创建网格，每行3张
    cols = st.columns(3)
    
    selected_imgs = []
    
    # 遍历全局的图片数据
    for idx, img_info in enumerate(state.images_data):
        col = cols[idx % 3]
        with col:
            # 从二进制数据还原图片
            image = Image.open(io.BytesIO(img_info['data']))
            st.image(image, use_column_width=True)
            
            # 显示当前票数
            current_count = state.votes.get(img_info['name'], 0)
            
            # 管理员模式显示得更清楚一点
            if admin_mode:
                 st.info(f"票数: {current_count}")
            else:
                 st.caption(f"当前票数: {current_count}")
            
            # 只有在非管理员模式下才显示勾选框
            if not admin_mode and state.voting_open:
                if st.checkbox(f"喜欢这件 (#{idx+1})", key=f"check_{img_info['name']}"):
                    selected_imgs.append(img_info['name'])
    
    if not admin_mode:
        st.divider()
    
    # 5. 提交逻辑 (只有非管理员模式才会渲染这个按钮)
    if not admin_mode and state.voting_open:
        # 这个按钮现在安全地在 st.form 里面
        submitted = st.form_submit_button("✅ 提交我的选择", type="primary")
        
        if submitted:
            if not voter_name:
                st.error("❌ 请先输入名字！")
            elif voter_name in state.voters:
                st.warning(f"{voter_name}，你已经投过票了，不能重复投哦。")
            elif not selected_imgs:
                st.warning("你还没选任何衣服呢！")
            else:
                # --- 更新全局数据 ---
                for name in selected_imgs:
                    state.votes[name] += 1
                state.voters.append(voter_name)
                
                st.balloons()
                st.success("投票成功！感谢参与。")
                import time
                time.sleep(1)
                st.rerun()