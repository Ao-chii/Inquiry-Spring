<template>
  <!-- 主容器，使用与chatPage一致的背景色 -->
  <el-container style="height: 100vh; background: linear-gradient(135deg, #f5f1e8 0%, #f0e6d2 100%)">
    <!-- 侧边栏导航 -->
    <el-aside width="240px" style="background: #f1e9dd; border-right: 1px solid #e0d6c2; border-radius: 0 12px 12px 0; box-shadow: 2px 0 10px rgba(0,0,0,0.05);overflow-x: hidden">
      <el-row :gutter="20">
        <div style="color: #5a4a3a; padding: 15px; font-size: 18px; font-weight: bold; display: flex; align-items: center;">
          <i class="el-icon-connection" style="margin-right: 8px; color: #8b7355"></i>
          <span>问泉-Inquiry Spring</span>
        </div>   
      </el-row>
      <el-menu 
        background-color="#f1e9dd"
        text-color="#5a4a3a"
        active-text-color="#ffffff"
        :default-active="'1'">
        <el-menu-item index="1" style="border-radius: 8px; margin: 8px; width: calc(100% - 16px); background: #8b7355; color: white; box-shadow: 0 2px 8px rgba(139, 115, 85, 0.2)">
          <i class="el-icon-folder-add" style="color: white"></i>
          <span>管理学习项目</span>
        </el-menu-item>
        <el-menu-item @click="unlog" index="2" style="border-radius: 8px; margin: 8px; width: calc(100% - 16px); transition: all 0.3s">
          <i class="el-icon-right" style="color: #8b7355"></i>
          <span>退出</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-main style="padding: 20px;">
        <!-- 项目创建表单 -->
        <div class="project-form" style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); margin-bottom: 20px;">
          <h2 style="color: #5a4a3a; margin-bottom: 20px;">创建新学习项目</h2>
          
          <el-form ref="projectForm" :model="projectForm" label-width="100px">
            <!-- 项目名称输入 -->
            <el-form-item label="项目名称" prop="name" required>
              <el-input 
                v-model="projectForm.name" 
                placeholder="输入项目名称"
                style="width: 300px;"
                clearable>
              </el-input>
            </el-form-item>

            <!-- 项目描述输入 -->
            <el-form-item label="项目描述" prop="description">
              <el-input
                type="textarea"
                :rows="2"
                v-model="projectForm.description"
                placeholder="输入项目描述"
                style="width: 80%;"
                maxlength="200"
                show-word-limit>
              </el-input>
            </el-form-item>

            <!-- 文件上传区域 -->
            <el-form-item label="上传资料">
              <el-tooltip content="上传相关文件作为学习项目的知识库" placement="right">
                <i class="el-icon-question" style="color: #8b7355; font-size: 16px;"></i>
              </el-tooltip>
              <el-upload
                class="upload-demo"
                drag
                :action="this.uploadUrl"
                multiple
                :on-success="handleUploadSuccess"
                :before-upload="beforeUpload"
                style="width: 80%;">
                <i class="el-icon-upload" style="color: #8b7355; font-size: 48px;"></i>
                <div class="el-upload__text" style="color: #5a4a3a;">将文件拖到此处，或<em style="color: #8b7355;">点击上传</em></div>
                <div class="el-upload__tip" slot="tip" style="color: #8b7355;">支持word/pdf/txt格式</div>
              </el-upload>
            </el-form-item>

            <!-- 提交按钮 -->
            <el-form-item>
              <el-button 
                type="primary" 
                @click="submitProject" 
                style="background: #8b7355; border: none; padding: 12px 24px;"
                :loading="isSubmitting">
                创建项目
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 项目列表展示 -->
        <div class="project-list" style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.05);">
          <h2 style="color: #5a4a3a; margin-bottom: 20px;">我的学习项目</h2>
          
          <el-table
            :data="projects"
            style="width: 100%"
            empty-text="暂无项目，请先创建一个项目">
            <el-table-column
              prop="name"
              label="项目名称"
              width="180">
            </el-table-column>
            <el-table-column
              prop="description"
              label="项目描述">
            </el-table-column>
            <el-table-column
              prop="createTime"
              label="创建时间"
              width="180">
            </el-table-column>
            <el-table-column
              label="操作"
              width="120">
              <template #default="scope">
                <el-button 
                  @click="openProject(scope.row)" 
                  type="text" 
                  style="color: #8b7355;">
                  打开
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
export default {
  data() {
    return {
      uploadUrl:this.HOST+'/fileUpload/',
      // 项目表单数据
      projectForm: {
        name: '',
        description: '',
        files: []
      },
      // 项目列表数据
      projects: [
        // 示例数据
        {
          id: 1,
          name: '机器学习入门',
          description: '学习机器学习基础知识',
          createTime: '2025-05-15'
        },
        {
          id: 2,
          name: 'Vue3高级教程',
          description: '深入学习Vue3框架',
          createTime: '2025-05-20'
        }
      ],
      isSubmitting: false
    }
  },
  methods: {
    // 上传文件前的校验
    beforeUpload(file) {
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        this.$message.error('上传文件大小不能超过10MB!');
      }
      return isLt10M;
    },
    // 文件上传成功处理
    handleUploadSuccess(response, file) {
      this.projectForm.files.push({
        name: file.name,
        url: response.url
      });
      this.$message.success(`${file.name} 上传成功`);
    },
    // 提交项目表单
    submitProject() {
      this.isSubmitting = true;
      // 这里应该是调用API创建项目的逻辑
      // 模拟API调用
      setTimeout(() => {
        this.projects.unshift({
          id: Date.now(),
          name: this.projectForm.name,
          description: this.projectForm.description,
          createTime: new Date().toLocaleDateString()
        });
        
        this.$message.success('项目创建成功');
        this.projectForm = {
          name: '',
          description: '',
          files: []
        };
        this.isSubmitting = false;
      }, 3000);
    },
    // 打开项目
    openProject(row) {
      //将当前项目状态信息存入store
      this.$store.dispatch('updateSelectedPrjId', row.id);
      this.$store.dispatch('updateSelectedPrjName', row.name);

      this.$message.info(`打开项目: ${row.name}`);
      this.$router.push({ path: '/chat', query: { id: row.id } });
      // 实际应用中这里应该跳转到项目详情页
      // this.$router.push(`/project/${project.id}`);
    },
    // 跳转到聊天页面
    unlog() {
      window.alert('退出')
      this.$router.push('/')
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
