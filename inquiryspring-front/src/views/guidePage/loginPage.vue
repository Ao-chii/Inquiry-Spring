<template>
  <!-- 主容器，使用与homePage一致的背景色 -->
  <el-container style="height: 100vh; background: linear-gradient(135deg, #f5f1e8 0%, #f0e6d2 100%)">
    <el-container style="display: flex; justify-content: center; align-items: center;">
      <el-card class="login-card" style="width: 800px; padding: 40px;">
        <div style="display: flex; justify-content: space-between;">
          <!-- 左侧走马灯展示系统功能 -->
          <div style="width: 45%;">
            <el-carousel height="400px" indicator-position="outside">
              <el-carousel-item v-for="(item, index) in features" :key="index">
                <div class="feature-item" :style="{ background: item.bgColor }">
                  <i :class="item.icon" style="font-size: 48px; color: white;"></i>
                  <h3 style="color: white; margin-top: 20px;">{{ item.title }}</h3>
                  <p style="color: white; margin-top: 10px;">{{ item.description }}</p>
                </div>
              </el-carousel-item>
            </el-carousel>
          </div>

          <!-- 右侧登录/注册表单 -->
          <div style="width: 45%;">
            <h2 style="text-align: center; color: #8b7355;">问泉-Inquiry Spring</h2>
            <el-tabs v-model="activeTab" style="margin-top: 20px;">
              <el-tab-pane label="登录" name="login">
                <el-form :model="loginForm" :rules="loginRules" ref="loginForm" label-width="0px">
                  <el-form-item prop="username">
                    <el-input v-model="loginForm.username" prefix-icon="el-icon-user" placeholder="用户名"></el-input>
                  </el-form-item>
                  <el-form-item prop="password">
                    <el-input v-model="loginForm.password" prefix-icon="el-icon-lock" type="password" placeholder="密码"></el-input>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" style="width: 100%; background: linear-gradient(135deg, #a0866b 0%, #d4b999 100%); border-color: #8b7355;" @click="handleLogin">登录</el-button>
                  </el-form-item>
                </el-form>
              </el-tab-pane>

              <el-tab-pane label="注册" name="register">
                <el-form :model="registerForm" :rules="registerRules" ref="registerForm" label-width="0px">
                  <el-form-item prop="username">
                    <el-input v-model="registerForm.username" prefix-icon="el-icon-user" placeholder="用户名"></el-input>
                  </el-form-item>
                  <el-form-item prop="password">
                    <el-input v-model="registerForm.password" prefix-icon="el-icon-lock" type="password" placeholder="密码"></el-input>
                  </el-form-item>
                  <el-form-item prop="confirmPassword">
                    <el-input v-model="registerForm.confirmPassword" prefix-icon="el-icon-lock" type="password" placeholder="确认密码"></el-input>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" style="width: 100%; background: linear-gradient(135deg, #a0866b 0%, #d4b999 100%); border-color: #8b7355;" @click="handleRegister">注册</el-button>
                  </el-form-item>
                </el-form>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
      </el-card>
    </el-container>
  </el-container>
</template>

<script>
import axios from 'axios'

export default {
  name: 'LoginPage',
  data() {
    // 密码确认验证
    const validateConfirmPassword = (rule, value, callback) => {
      if (value !== this.registerForm.password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    }

    return {
      activeTab: 'login',
      // 登录表单数据
      loginForm: {
        username: '',
        password: ''
      },
      // 注册表单数据
      registerForm: {
        username: '',
        password: '',
        confirmPassword: ''
      },
      // 登录表单验证规则
      loginRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
        ]
      },
      // 注册表单验证规则
      registerRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请确认密码', trigger: 'blur' },
          { validator: validateConfirmPassword, trigger: 'blur' }
        ]
      },
      // 功能展示数据
      features: [
        {
          title: '学习项目管理',
          description: '高效管理您的学习项目，追踪学习进度',
          icon: 'el-icon-folder',
          bgColor: 'linear-gradient(135deg, #a0866b 0%, #d4b999 100%)'
        },
        {
          title: '智能答疑',
          description: 'AI大模型智能解答您的学习疑问',
          icon: 'el-icon-chat-dot-round',
          bgColor: 'linear-gradient(135deg, #8b7355 0%, #a0866b 100%)'
        },
        {
          title: '智慧总结',
          description: '自动生成学习要点总结，提高学习效率',
          icon: 'el-icon-notebook-2',
          bgColor: 'linear-gradient(135deg, #d4b999 0%, #f0e6d2 100%)'
        },
        {
          title: '智能小测验',
          description: '个性化测验，巩固学习成果',
          icon: 'el-icon-edit-outline',
          bgColor: 'linear-gradient(135deg, #a0866b 0%, #d4b999 100%)'
        }
      ]
    }
  },
  
  methods: {
    /**
     * 处理用户登录
     * 1. 验证表单数据
     * 2. 发送登录请求到后端
     * 3. 根据响应结果处理登录状态
     *    - 成功：显示成功消息并跳转到项目页面
     *    - 失败：显示错误消息
     */
    handleLogin() {
      this.$refs.loginForm.validate(async (valid) => {
        if (valid) {
          try {
            console.log('发送登录请求...');
            const response = await axios.post('/api/login/', this.loginForm)
            console.log('登录响应:', response.data);
            
            if (response.data.success) {
              // 直接使用表单中的用户名
              const username = this.loginForm.username;
              console.log('使用表单用户名:', username);
              
              // 更新Vuex store中的用户信息
              await this.$store.dispatch('updateUserInfo', {
                username: username
              });
              
              // 验证store是否更新成功
              const storeUsername = this.$store.getters.getUsername;
              console.log('Store中的用户名:', storeUsername);
              
              this.$message.success('登录成功')
              this.$router.push('/project')
            } else {
              console.error('登录失败:', response.data.message);
              this.$message.error(response.data.message || '登录失败')
            }
          } catch (error) {
            console.error('登录失败:', error);
            if (error.response) {
              console.error('错误响应:', error.response.data);
              console.error('状态码:', error.response.status);
            }
            this.$message.error('登录请求失败，请稍后重试')
          }
        }
      })
    },

    /**
     * 处理用户注册
     * 1. 验证表单数据（包括密码确认）
     * 2. 发送注册请求到后端
     * 3. 根据响应结果处理注册状态
     *    - 成功：显示成功消息并切换到登录标签页
     *    - 失败：显示错误消息
     */
    handleRegister() {
      this.$refs.registerForm.validate(async (valid) => {
        if (valid) {
          try {
            const response = await axios.post('/api/register/', {
              username: this.registerForm.username,
              password: this.registerForm.password
            })
            if (response.data.success) {
              this.$message.success('注册成功')
              this.activeTab = 'login'
              // 自动填充登录表单
              this.loginForm.username = this.registerForm.username;
              this.loginForm.password = this.registerForm.password;
            } else {
              this.$message.error(response.data.message || '注册失败')
            }
          } catch (error) {
            this.$message.error('注册请求失败，请稍后重试')
          }
        }
      })
    }
  }
}
</script>

<style scoped>
/* 登录卡片样式 */
.login-card {
  border: 1px solid rgba(139, 115, 85, 0.1);
  border-radius: 8px;
  transition: all 0.3s;
}

.login-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(139, 115, 85, 0.15);
}

/* 功能展示项样式 */
.feature-item {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

/* 表单样式 */
.el-form-item {
  margin-bottom: 20px;
}

.el-input__inner {
  border-radius: 4px;
  border: 1px solid #d4b999;
}

.el-input__inner:focus {
  border-color: #8b7355;
}

/* 按钮悬停效果 */
.el-button:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}
</style>
