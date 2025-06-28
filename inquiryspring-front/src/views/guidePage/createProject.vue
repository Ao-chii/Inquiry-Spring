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

     <!-- 学习计划卡片 -->
      <!-- <div 
          @click="gotoTaskManage" 
          class="study-plan-card"
      >
          <i class="el-icon-date" style="color: #d48806"></i>
          <span>我的学习计划</span>
      </div> -->

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
            <el-form-item label="项目名称" prop="name">
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
            
            <div class="upload-section" style="background: #f9f5ee; padding: 20px; border-radius: 8px; margin-bottom: 10px; position: relative;">
              <h3 style="color: #5a4a3a; margin-bottom: 15px; border-bottom: 1px solid #e0d6c2; padding-bottom: 10px;">上传新文档</h3>
              <el-upload
                class="upload-demo"
                drag
                :action="getUploadUrl()"
                multiple
                :on-success="handleUploadSuccess"
                :before-upload="beforeUpload"
                :show-file-list="false"
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
                  width="580">
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
              width="280">
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
              width="280">
              <template #default="scope">
                <el-button 
                  @click="openProject(scope.row)" 
                  type="text" 
                  style="color: #8b7355;">
                  开始学习
                </el-button>
                <el-button 
                  @click="showManageDialog(scope.row)" 
                  type="text" 
                  style="color: #8b7355;">
                  管理文档
                </el-button>
                <el-button 
                  @click="deleteProject(scope.row)" 
                  type="text" 
                  style="color: #f56c6c; font-weight: bold;">
                  删除
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
      url:this.HOST+'/projects/',
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
      projects: [],
      isSubmitting: false,
      uploadLoading: false // 新增：文档上传loading状态
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
    // 文件上传成功处理
    handleUploadSuccess(response, file) {
      if (this.uploadLoadingInstance) {
        this.uploadLoadingInstance.close();
        this.uploadLoadingInstance = null;
      }
      this.uploadLoading = false;
      if (response.data && response.data.document_id) {
        // 上传成功后将文档加入当前项目文档列表
        if (this.currentProject) {
          if (!Array.isArray(this.currentProject.documents)) {
            // 关键修复：首次上传时初始化documents为数组
            this.$set(this.currentProject, 'documents', []);
          }
          this.currentProject.documents.push({
            name: response.data.filename,
            size: file.size ? Math.round(file.size / 1024) + 'KB' : '未知',
            uploadTime: new Date().toLocaleString(),
            url: response.data.url
          });
        }
        this.$message.success(`${file.name} 上传成功`);
      } else {
        this.$message.error(response?.error || `${file.name} 上传失败`);
      }
    },
    // 上传文件前的校验
    beforeUpload(file) {
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        this.$message.error('上传文件大小不能超过10MB!');
      }
      if (isLt10M) {
        this.uploadLoading = true;
        // 全局遮罩
        this.uploadLoadingInstance = this.$loading({
          lock: true,
          text: '正在处理上传文档，请稍候...',
          background: 'rgba(255,255,255,0.7)'
        });
      }
      return isLt10M;
    },
    // 提交项目表单
    submitProject() {
      this.isSubmitting = true;
      // 构造请求数据，包含用户名
      const payload = {
        name: this.projectForm.name,
        description: this.projectForm.description,
        username: this.username // 传递当前登录用户名
      };
      axios.post(this.url, payload, {
        withCredentials: true // 携带cookie/session认证
      })
        .then(res => {
          if (res.data && res.data.data.project) {
            this.projects.unshift({
              id: res.data.data.project.id,
              name: res.data.data.project.name,
              description: res.data.data.project.description,
              createTime: res.data.data.project.createTime
            });
            this.$message.success('项目创建成功');
            this.projectForm = { name: '', description: '', files: [] };
          } else {
            this.$message.error(res.data.error || '项目创建失败');
          }
        })
        .catch(err => {
          this.$message.error(err.response?.data?.data.error || '项目创建失败,err');
        })
        .finally(() => {
          this.isSubmitting = false;
        });
    },
    // 打开项目
    openProject(row) {
      //将当前项目状态信息存入store
      this.$store.dispatch('setCurrentProject', row);
      // 同步存入localStorage
      localStorage.setItem('currentProject', JSON.stringify(row));
      this.$message.info(`打开项目: ${row.name}`);
      this.$router.push({ path: '/chat', query: { id: row.id } });
      // 实际应用中这里应该跳转到项目详情页
      // this.$router.push(`/project/${project.id}`);
    },
    // 退出登录
    async unlog() {
      this.$router.push('/');
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
    },
    // 获取用户所有项目
    fetchUserProjects() {
      axios.get(this.url, {
        params: { username: this.username },
        withCredentials: true
      })
        .then(res => {
          if (Array.isArray(res.data.data)) {
            this.projects = res.data.data;
          } else {
            this.projects = [];
          }
        })
        .catch(() => {
          this.projects = [];
        });
    },

    gotoTaskManage() {
      this.$router.push({ path: '/manage' });
    },

    deleteProject(row) {
      this.$confirm(`确定要删除项目“${row.name}”吗？此操作不可恢复！`, '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        axios.post(this.HOST + `/projects/${row.id}/deleteProject/`, {}, {
          withCredentials: true
        }).then(res => {
          const data = res.data && res.data.data ? res.data.data : res.data;
          if (data && data.success) {
            this.$message.success('项目删除成功');
            this.projects = this.projects.filter(p => p.id !== row.id);
          } else {
            this.$message.error(data.error || '删除失败');
          }
        }).catch(err => {
          this.$message.error(err.response?.data?.error || '删除失败');
        });
      }).catch(() => {
        this.$message.info('已取消删除');
      });
    },

    deleteDocument(row) {
      if (!this.currentProject || !this.currentProject.id) {
        this.$message.error('未找到当前项目');
        return;
      }
      this.$confirm(`确定要删除文档“${row.name}”吗？此操作不可恢复！`, '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        axios.post(this.HOST + `/projects/${this.currentProject.id}/documents/deleteDocument`, {
          filename: row.name
        }, {
          withCredentials: true
        }).then(res => {
          const data = res.data && res.data.data ? res.data.data : res.data;
          if (data && data.success) {
            this.$message.success('文档删除成功');
            this.currentProject.documents = this.currentProject.documents.filter(d => d.name !== row.name);
          } else {
            this.$message.error(data.error || '删除失败');
          }
        }).catch(err => {
          this.$message.error(err.response?.data?.error || '删除失败');
        });
      }).catch(() => {
        this.$message.info('已取消删除');
      });
    },
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
    this.fetchUserProjects(); // 页面加载后调用
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

.study-plan-card {
      margin: 24px 8px 0 8px;
      width: calc(100% - 16px);
      border-radius: 8px;
      background: #fff7e6;
      color: #d48806;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 15px;
      font-weight: 500;
      gap: 8px;
      box-shadow: 0 2px 8px rgba(212,136,6,0.08);
      padding: 12px 0;
      transition: background 0.2s, transform 0.18s, box-shadow 0.18s;
  }
  .study-plan-card:hover {
      background: #ffe7ba;
      transform: scale(1.045);
      box-shadow: 0 6px 18px rgba(212,136,6,0.18);
  }
</style>
