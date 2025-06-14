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

      <!-- 用户信息展示 -->
      <div class="user-info" style="position: fixed; bottom: 0; left: 0; width: 240px; padding: 15px; border-top: 1px solid #e0d6c2; background: #f1e9dd;">
        <div style="display: flex; align-items: center; padding: 10px;">
          <el-avatar :size="40" style="background: #8b7355; margin-right: 10px;">
            {{ userInitial }}
          </el-avatar>
          <div>
            <div style="color: #5a4a3a; font-weight: bold; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px;">{{ username }}</div>
            <div style="color: #8b7355; font-size: 12px;">已登录</div>
          </div>
        </div>
      </div>
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
            <!-- <el-form-item label="上传资料">
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
            </el-form-item> -->

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

        <!-- 文档管理对话框 -->
        <el-dialog 
          title="项目管理"
          :visible.sync="manageDialogVisible" 
          width="70%"
          custom-class="project-manage-dialog"
          :close-on-click-modal="false">
          <div class="dialog-content">
            <div class="project-info" style="background: #f9f5ee; padding: 20px; border-radius: 8px; margin-bottom: 10px; display: flex; align-items: center; gap: 20px;">
              <h3 style="color: #5a4a3a; margin: 0;">{{ currentProject.name }}</h3>
              <p style="color: #8b7355; margin: 0;">{{ currentProject.description }}</p>
            </div>
            
            <div class="upload-section" style="background: #f9f5ee; padding: 20px; border-radius: 8px; margin-bottom: 10px;">
              <h3 style="color: #5a4a3a; margin-bottom: 15px; border-bottom: 1px solid #e0d6c2; padding-bottom: 10px;">上传新文档</h3>
              <el-upload
                class="upload-demo"
                drag
                :action="getUploadUrl()"
                multiple
                :on-success="handleUploadSuccess"
                :before-upload="beforeUpload"
                style="width: 100%;">
                <i class="el-icon-upload" style="color: #8b7355; font-size: 48px;"></i>
                <div class="el-upload__text" style="color: #5a4a3a;">将文件拖到此处，或<em style="color: #8b7355;">点击上传</em></div>
                <div class="el-upload__tip" slot="tip" style="color: #8b7355;">支持word/pdf/txt格式</div>
              </el-upload>
            </div>
            
            <div class="documents-section" style="background: #f9f5ee; padding: 20px; border-radius: 8px;">
              <h3 style="color: #5a4a3a; margin-bottom: 15px; border-bottom: 1px solid #e0d6c2; padding-bottom: 10px;">当前项目文档</h3>
              <el-table
                :data="currentProject ? currentProject.documents : []"
                style="width: 100%"
                empty-text="暂无文档">
                <el-table-column
                  prop="name"
                  label="文档名称"
                  width="180">
                </el-table-column>
                <el-table-column
                  prop="size"
                  label="大小"
                  width="120">
                </el-table-column>
                <el-table-column
                  prop="uploadTime"
                  label="上传时间"
                  width="180">
                </el-table-column>
                <el-table-column
                  label="操作"
                  width="120">
                  <template #default="scope">
                    <el-button 
                      @click="deleteDocument(scope.row)" 
                      type="text" 
                      style="color: #f56c6c;">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          
          <span slot="footer" class="dialog-footer">
            <el-button @click="manageDialogVisible = false" style="color: #5a4a3a;">取消</el-button>
            <el-button type="primary" @click="manageDialogVisible = false" style="background: #8b7355; border: none;">确定</el-button>
          </span>
        </el-dialog>
        
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
              width="180">
              <template #default="scope">
                <el-button 
                  @click="openProject(scope.row)" 
                  type="text" 
                  style="color: #8b7355;">
                  打开
                </el-button>
                <el-button 
                  @click="showManageDialog(scope.row)" 
                  type="text" 
                  style="color: #8b7355;">
                  管理
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
import { mapGetters } from 'vuex'
import axios from 'axios'

export default {
  data() {
    return {
      uploadUrl:this.HOST+'/fileUpload/',
      // 文档管理对话框状态
      manageDialogVisible: false,
      currentProject: {
        id: null,
        name: '',
        description: ''
      },
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
  computed: {
    ...mapGetters(['getUsername', 'isLoggedIn']),
    username() {
      console.log('当前store中的用户名:', this.getUsername);
      const username = this.getUsername;
      if (!username && this.isLoggedIn) {
        console.warn('已登录但用户名为空');
      }
      return username || '未登录'
    },
    userInitial() {
      const username = this.getUsername;
      console.log('计算用户名首字母，用户名:', username);
      return username ? username.charAt(0).toUpperCase() : '?'
    }
  },
  watch: {
    // 监听用户名变化
    getUsername: {
      immediate: true,
      handler(newUsername) {
        console.log('用户名更新:', newUsername);
      }
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
      this.$store.dispatch('setCurrentProject', row);

      this.$message.info(`打开项目: ${row.name}`);
      this.$router.push({ path: '/chat', query: { id: row.id } });
      // 实际应用中这里应该跳转到项目详情页
      // this.$router.push(`/project/${project.id}`);
    },
    // 退出登录
    async unlog() {
      this.$router.push('/');
      // try {
      //   await axios.post('/api/logout/', {}, {
      //     withCredentials: true,
      //     headers: {
      //       'Content-Type': 'application/json',
      //     }
      //   });
      //   await this.$store.dispatch('logout');
      //   this.$message.success('退出成功');
      //   this.$router.push('/');
      // } catch (error) {
      //   console.error('退出失败:', error);
      //   this.$message.error('退出失败，请重试');
      // }
    },
    // 显示文档管理对话框
    showManageDialog(project) {
      this.currentProject = project;
      this.$store.dispatch('setCurrentProject', project);
      this.manageDialogVisible = true;
    },
    
    // 获取上传URL
    getUploadUrl() {
      return this.HOST + '/projects/' + (this.currentProject?.id || '') + '/documents/';
    },
    
    // 检查登录状态
    async checkLoginStatus() {
      console.log('检查登录状态:', this.isLoggedIn);
      console.log('当前用户名:', this.username);
      
      if (!this.isLoggedIn) {
        console.log('未登录，准备跳转到登录页');
        this.$message.warning('请先登录');
        this.$router.push('/');
        return;
      }
      
      // 如果已登录但没有用户名，尝试重新获取用户信息
      if (this.isLoggedIn && !this.getUsername) {
        console.log('已登录但无用户名，尝试获取用户信息');
        try {
          const response = await axios.get('/api/user/info/', {
            withCredentials: true
          });
          console.log('获取用户信息响应:', response.data);
          
          if (response.data.success) {
            await this.$store.dispatch('updateUserInfo', {
              username: response.data.username
            });
            console.log('用户信息更新成功');
          }
        } catch (error) {
          console.error('获取用户信息失败:', error);
        }
      }
    }
  },
  
  async created() {
    // 检查localStorage中是否有用户信息
    const userInfo = localStorage.getItem('userInfo');
    // 将JSON字符串转换为对象
    const parsedUserInfo = JSON.parse(userInfo);
    // 触发Vuex action来更新store中的用户信息
    this.$store.dispatch('restoreUserInfo', parsedUserInfo);

    console.log('组件创建，当前登录状态:', this.isLoggedIn);
    console.log('组件创建，当前用户名:', this.getUsername);
    
    // 组件创建时检查登录状态
    await this.$nextTick();
    await this.checkLoginStatus();
  }
}
</script>

<style scoped>
.project-manage-dialog {
  border-radius: 12px !important;
}

.dialog-content {
  max-height: 70vh;
  overflow-y: auto;
  padding: 10px;
}
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

/* 用户信息样式 */
.user-info {
  background: #f1e9dd;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
  z-index: 1000;
  transition: all 0.3s ease;
}

.user-info:hover {
  background: #e9e0d2;
}

/* 确保侧边栏内容不被用户信息遮挡 */
.el-aside {
  position: relative;
  padding-bottom: 80px; /* 为用户信息区域留出空间 */
}

/* 用户名文本溢出处理 */
.el-avatar {
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 主内容区域样式 */
.el-main {
  overflow-y: auto;
  height: 100vh;
}

/* 设置滚动条样式 */
.el-main::-webkit-scrollbar {
  width: 6px;
}

.el-main::-webkit-scrollbar-thumb {
  background-color: rgba(139, 115, 85, 0.2);
  border-radius: 3px;
}

.el-main::-webkit-scrollbar-track {
  background-color: transparent;
}
</style>
