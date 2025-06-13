<template>
  <!-- 主容器，使用与chatPage一致的背景色 -->
  <el-container style="height: 100vh; background: linear-gradient(135deg, #f5f1e8 0%, #f0e6d2 100%)">
    <!-- 主内容区 -->
    <el-container style="display: flex; justify-content: center; align-items: center;">
      <el-card class="project-card" style="width: 600px; padding: 80px;">
        <h2 style="text-align: center; color: #8b7355;">问泉-Inquiry Spring</h2>
        <p style="text-align: center; color: #8b7355; margin-top: 15px;">
          开始您的学习之旅
        </p>
        <div style="display: flex; justify-content: center; margin-top: 30px;">
          <el-button 
            type="primary" 
            icon="el-icon-right" 
            circle 
            style="
              background: linear-gradient(135deg, #a0866b 0%, #d4b999 100%);
              border-color: #8b7355;
              width: 50px;
              height: 50px;
              font-size: 18px;
            "
            @click="toMainPage">
          </el-button>
        </div>
      </el-card>
    </el-container>
  </el-container>
</template>

<script>
    export default {
        methods: {
            toMainPage() {
                this.$router.push('/project')
            }
        }
    }
</script>

<style scoped>
/* 使用与chatPage一致的样式 */
.el-menu-item {
  transition: all 0.3s ease;
}

.el-menu-item:hover {
  background-color: #d4c9a8;
}

.el-menu-item.is-active {
  background: linear-gradient(135deg, #a0866b 0%, #d4b999 100%) !important;
  color: white !important;
  box-shadow: 0 2px 8px rgba(139, 115, 85, 0.3) !important;
  transform: translateY(-1px);
}

.el-menu-item.is-active i {
  color: white !important;
}

/* 项目卡片样式 */
.project-card {
  margin-bottom: 20px;
  border: 1px solid rgba(139, 115, 85, 0.1);
  border-radius: 8px;
  transition: all 0.3s;
}

.project-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(139, 115, 85, 0.15);
}
</style>