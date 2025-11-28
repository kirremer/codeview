import streamlit as st
import pandas as pd
from PIL import Image
import io
import os
import threading # 引入线程锁，解决并发问题

# --- 页面基础配置 ---
st.set_page_config(page_title="衣服投票", layout="wide")

# 确保本地 images 文件夹存在
if not os.path.exists("images"):
    os.makedirs("images")

# --- 全局状态管理 ---
@st.cache_resource
class GlobalState:
    def __init__(self):
        self.votes = {}        # 存储票数
        self.voters = []       # 存储已投票的人
        self.voting_open = True 
        self.lock = threading.Lock() # 🔒 核心：创建一个锁，防止数据冲突
    
    def get_all_images(self):
        """获取 images 文件夹下的所有图片"""
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
        image_files = []
        
        # 扫描 images 文件夹
        if os.path.exists("images"):
            files = sorted([f for f in os.listdir("images") if f.lower().endswith(valid_extensions)])
            for f in files:
                image_files.append(os.path.join("images", f))
        
        return image_files

    def save_uploaded_image(self, uploaded_file):
        """
        核心修复：将网页上传的图片直接保存到服务器磁盘
        并进行压缩，防止卡顿
        """
        try:
            image = Image.open(uploaded_file)
            
            # ⚡️ 性能优化：如果图片太大，进行压缩 (最大宽度 800px)
            max_width = 800
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height))
            
            # 保存到 images 文件夹
            save_path = os.path.join("images", uploaded_file.name)
            
            # 如果文件名重复，自动改名
            if os.path.exists(save_path):
                base, ext = os.path.splitext(uploaded_file.name)
                save_path = os.path.join("images", f"{base}_new{ext}")
            
            # 保存文件
            image.save(save_path, optimize=True, quality=85)
            
            # 初始化票数
            file_name = os.path.basename(save_path)
            with self.lock: # 加锁操作
                if file_name not in self.votes:
                    self.votes[file_name] = 0
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False

    def cast_vote(self, voter_name, selected_imgs):
        """安全投票逻辑"""
        with self.lock: # 🔒 加锁：确保同一时间只有一个人能修改数据
            if voter_name in self.voters:
                return False, "你已经投过票了！"
            
            for name in selected_imgs:
                if name not in self.votes:
                    self.votes[name] = 0
                self.votes[name] += 1
            
            self.voters.append(voter_name)
            return True, "投票成功！"

# 获取全局状态
state = GlobalState()

# 获取当前所有图片
current_images = state.get_all_images()

# --- 侧边栏：管理员面板 ---
with st.sidebar:
    st.header("🔧 管理面板")
    
    admin_mode = st.checkbox("我是发起人 (管理/上传)")
    
    if admin_mode:
        st.write("---")
        st.subheader("📤 网页上传图片")
        st.info("原理：图片会保存到服务器临时磁盘，所有人立即可见。")
        
        uploaded_files = st.file_uploader(
            "上传新图片 (自动压缩)", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("确认添加并发布"):
                success_count = 0
                for f in uploaded_files:
                    if state.save_uploaded_image(f):
                        success_count += 1
                
                if success_count > 0:
                    st.success(f"成功发布 {success_count} 张图片！")
                    st.rerun() # 强制刷新，让新图显示出来

        st.write("---")
        st.subheader("📊 投票统计")
        total_votes = sum(state.votes.values())
        st.write(f"图片总数: {len(current_images)}")
        st.write(f"总票数: {total_votes}")
        st.write(f"参与人数: {len(state.voters)}")
        
        if st.button("生成 Excel 结果"):
            data = []
            for img_path in current_images:
                name = os.path.basename(img_path)
                data.append({
                    "衣服文件名": name,
                    "获得票数": state.votes.get(name, 0)
                })
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载结果 CSV", csv, "results.csv", "text/csv")
            
        with st.expander("危险操作"):
            if st.button("清空投票数据"):
                with state.lock:
                    state.votes = {}
                    state.voters = []
                    # 重新初始化现有图片的票数
                    for img_path in current_images:
                        name = os.path.basename(img_path)
                        state.votes[name] = 0
                st.rerun()

# --- 主界面 ---
st.title("👔 衣服挑选投票")

if not current_images:
    st.warning("暂无图片。管理员请在左侧上传。")
    if not admin_mode:
        st.stop()

# 身份输入
if not admin_mode:
    st.write("👇 请勾选你喜欢的衣服，然后点击底部的提交按钮。")
    voter_name = st.text_input("请输入你的名字", placeholder="例如：Alex")

# 投票表单
if not admin_mode:
    content_container = st.form("vote_form")
else:
    content_container = st.container()

with content_container:
    cols = st.columns(3) # 默认3列
    selected_imgs = []
    
    for idx, img_path in enumerate(current_images):
        col = cols[idx % 3]
        file_name = os.path.basename(img_path)
        
        with col:
            try:
                image = Image.open(img_path)
                st.image(image, use_column_width=True)
                
                current_count = state.votes.get(file_name, 0)
                
                if admin_mode:
                    st.info(f"票数: {current_count}")
                else:
                    st.caption(f"当前票数: {current_count}")
                
                if not admin_mode:
                    if st.checkbox(f"喜欢这件 (#{idx+1})", key=file_name):
                        selected_imgs.append(file_name)
            except Exception as e:
                st.error("图片加载错")

    if not admin_mode:
        st.write("---")
        submitted = st.form_submit_button("✅ 提交我的选择", type="primary")
        
        if submitted:
            if not voter_name:
                st.error("❌ 请先输入名字！")
            elif not selected_imgs:
                st.warning("请至少选择一件衣服")
            else:
                # 调用安全的投票函数
                success, msg = state.cast_vote(voter_name, selected_imgs)
                if success:
                    st.balloons()
                    st.success(msg)
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning(msg)