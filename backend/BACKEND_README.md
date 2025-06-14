# InquirySpring Django Backend

这是InquirySpring项目的Django后端实现，提供AI驱动的学习助手功能。

## ✅ 开发状态

**当前状态**: 🎉 **开发完成并测试通过**

- ✅ Django REST Framework 配置完成
- ✅ SQLite 数据库配置和迁移完成
- ✅ 所有核心API端点正常工作
- ✅ AI服务集成（支持在线和离线模式）
- ✅ 前端兼容性接口完成
- ✅ 完整的API测试通过

## 🚀 快速启动

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 数据库初始化（已完成）
```bash
python manage.py migrate
```

### 3. 运行测试
```bash
# 基础API测试
python test_backend.py

# 详细功能测试
python test_api_detailed.py
```

### 4. 启动开发服务器
```bash
# 使用测试客户端（推荐）
python test_api_detailed.py

# 或使用简单服务器
python simple_server.py
```

## 🤖 AI服务配置

### 离线模式（当前）
- 默认运行在离线模拟模式
- 返回模拟的AI回复
- 无需API密钥即可测试所有功能

### 在线模式（可选）
创建 `.env` 文件启用真实AI功能：
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

## 📚 核心功能

### 🤖 AI服务
- **智能聊天**: 基于Gemini AI的对话功能
- **文档总结**: 自动生成文档摘要
- **测验生成**: 根据内容或主题生成测试题目
- **多模式支持**: 在线AI服务和离线模拟模式

### 📚 API端点
- **健康检查**: `GET /health/` - 服务状态检查
- **聊天对话**: `GET/POST /api/chat/` - 与AI进行智能对话
- **文档管理**: `GET/POST /api/documents/` - 文件上传、处理和总结
- **测验系统**: `GET/POST /api/quiz/` - 生成和管理测验
- **项目管理**: `GET /api/projects/` - 学习项目的创建和管理

### 🔧 技术架构
- **框架**: Django 4.2+ with Django REST Framework
- **数据库**: SQLite (开发环境)
- **AI服务**: Google Gemini API
- **前端兼容**: 与Vue.js前端完全兼容

### 3. 数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. 创建超级用户（可选）
```bash
python manage.py createsuperuser
```

### 5. 启动服务器
```bash
# 方式1: 使用Django命令
python manage.py runserver 0.0.0.0:8000

# 方式2: 使用启动脚本
python run_backend.py
```

### 6. 验证服务
访问 http://localhost:8000/health 检查服务状态

## API端点

### 聊天功能
- `POST /chat/` - 发送消息
- `GET /chat/` - 获取最新回复
- `GET /api/chat/history/` - 获取聊天历史

### 文档管理
- `POST /fileUpload/` - 上传文件
- `GET /summarize/?fileName=xxx` - 生成文档总结
- `GET /api/documents/list/` - 获取文档列表

### 测验系统
- `POST /test/` - 生成测验
- `POST /api/quiz/submit/` - 提交答案
- `GET /api/quiz/history/` - 获取测验历史

### 项目管理
- `GET /api/projects/` - 获取项目列表
- `POST /api/projects/` - 创建项目
- `GET /api/projects/{id}/` - 获取项目详情

## 前端集成

### Vue.js配置
在 `vue.config.js` 中配置代理：
```javascript
module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        }
      }
    }
  }
}
```

### API调用示例
```javascript
// 聊天
axios.post('/api/chat/', { message: '你好' })

// 文件上传
const formData = new FormData()
formData.append('file', file)
axios.post('/api/fileUpload/', formData)

// 生成测验
axios.post('/api/test/', {
  num: 5,
  difficulty: 'medium',
  types: ['MC', 'TF'],
  topic: '机器学习'
})
```

## 项目结构

```
inquiryspring-backend/
├── __init__.py
├── settings.py          # Django配置
├── urls.py             # URL路由
├── wsgi.py             # WSGI配置
├── chat/               # 聊天应用
├── documents/          # 文档管理应用
├── quiz/              # 测验应用
├── projects/          # 项目管理应用
└── ai_services/       # AI服务模块（主要AI功能）
    ├── rag_engine.py   # RAG引擎核心
    ├── llm_client.py   # LLM客户端
    ├── models.py       # AI服务数据模型
    └── prompt_manager.py # 提示词管理
```

## 开发说明

### 添加新功能
1. 在相应的应用中创建视图
2. 更新URL配置
3. 如需AI功能，直接使用 `ai_services.rag_engine.RAGEngine`

### AI服务扩展
- 修改 `ai_services/rag_engine.py` 添加新的AI功能
- 在 `ai_services/llm_client.py` 中添加新的LLM提供商
- 支持多种AI提供商和本地模型
- 提供离线模拟模式

### 数据库模型
- 使用Django ORM管理数据
- 支持数据迁移和版本控制
- 兼容多种数据库后端

## 部署

### 生产环境配置
1. 设置 `DEBUG=False`
2. 配置生产数据库（PostgreSQL/MySQL）
3. 设置静态文件服务
4. 配置HTTPS和安全设置


## 故障排除

### 常见问题
1. **AI服务不可用**: 检查GOOGLE_API_KEY环境变量
2. **CORS错误**: 确认django-cors-headers配置
3. **数据库错误**: 运行数据库迁移命令
4. **导入错误**: 检查Python路径和依赖安装

### 日志查看
- Django日志输出到控制台
- AI服务状态通过 `/health` 端点查看
- 使用Django admin查看数据库状态

## 贡献

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证。
