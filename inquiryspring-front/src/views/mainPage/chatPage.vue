<template>
    <el-container style="height: 100vh; background: linear-gradient(135deg, #f5f1e8 0%, #f0e6d2 100%)">
    <el-aside width="240px" style="background: linear-gradient(to bottom, #e8dfc8, #d8cfb8); border-right: 1px solid #d4c9a8; border-radius: 0 12px 12px 0; box-shadow: 2px 0 10px rgba(0,0,0,0.1);overflow-x: hidden">
        <el-row :gutter="20">
            <div style="color: #5a4a3a; padding: 15px; font-size: 18px; font-weight: bold; display: flex; flex-direction: column; align-items: center;">
                <div>
                    <i class="el-icon-connection" style="margin-right: 8px; color: #8b7355"></i>
                    <span>问泉-Inquiry Spring</span>
                </div>
                <div style="margin-top: 20px;">{{ this.$store.getters.getSelectedPrjName}}</div>
            </div>   
        </el-row>
        <el-menu 
            background-color="#e8dfc8"
            text-color="#5a4a3a"
            active-text-color="#ffffff"
            :default-active="'1'">
            <el-menu-item index="1" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px); background: linear-gradient(135deg, #5a4a3a 0%, #3a2e24 100%); color: white; box-shadow: 0 2px 8px rgba(90, 74, 58, 0.3)">
                <i class="el-icon-chat-dot-round" style="color: white"></i>
                <span>智能答疑</span>
            </el-menu-item>
            <el-menu-item @click="gotoSummarize" index="2" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px)">
                <i class="el-icon-notebook-2"></i>
                <span>智慧总结</span>
            </el-menu-item>
            <el-menu-item @click="gotoTest" index="3" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px)">
                <i class="el-icon-edit"></i>
                <span>生成小测</span>
            </el-menu-item>
            <el-menu-item @click="gotoPrj" style="border-radius: 8px; margin: 8px; width: calc(100% - 16px); transition: all 0.3s">
                <i class="el-icon-folder-add" style="color: #8b7355"></i>
                <span>管理学习项目</span>
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
    
    <el-container style="height: 100vh; overflow: hidden;">
        <el-main style="padding: 10px; display: flex; height: 100%; background-color: rgba(255,255,255,0.7); border-radius: 16px; margin: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid rgba(139, 115, 85, 0.1); overflow: hidden;">
            <div style="display: flex; width: 100%; height: 100%; gap: 20px;">
                <!-- 左侧聊天历史区域 - 固定 -->
                <div style="width: 300px; display: flex; flex-direction: column; height: 100%;">
                    <div class="sidebar-panel" style="height: 100%; display: flex; flex-direction: column;">
                        <div class="panel-header" style="flex-shrink: 0;">
                            <div class="header-title">
                                <i class="el-icon-chat-line-round"></i>
                                <span>聊天历史</span>
                            </div>
                            <div class="header-actions">
                                <el-tooltip content="新建对话" placement="top">
                                    <el-button
                                        @click="startNewChat"
                                        type="text"
                                        class="action-btn"
                                        size="mini">
                                        <i class="el-icon-plus"></i>
                                    </el-button>
                                </el-tooltip>
                                <el-tooltip content="清空历史" placement="top">
                                    <el-button
                                        @click="clearChatHistory"
                                        type="text"
                                        class="action-btn danger"
                                        size="mini">
                                        <i class="el-icon-delete"></i>
                                    </el-button>
                                </el-tooltip>
                            </div>
                        </div>

                        <div class="panel-content" style="flex: 1; overflow-y: auto;">


                            <div v-if="chatHistory.length" class="history-list">
                                <div
                                    v-for="session in chatHistory"
                                    :key="session.id"
                                    class="history-item"
                                    @click="loadChatSession(session)"
                                    :class="{ 'active': currentSessionId === session.id }"
                                >
                                    <div class="history-content">
                                        <div class="history-preview">{{ getSessionTitle(session) }}</div>
                                    </div>
                                    <div class="history-actions">
                                        <el-button
                                            @click.stop="deleteSession(session)"
                                            type="text"
                                            class="delete-session-btn"
                                            size="mini">
                                            <i class="el-icon-close"></i>
                                        </el-button>
                                    </div>
                                </div>
                            </div>
                            <div v-else class="empty-state">
                                <i class="el-icon-chat-dot-round"></i>
                                <p>暂无聊天记录</p>
                                <el-button @click="startNewChat" type="text" class="start-chat-btn">
                                    开始新对话
                                </el-button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 右侧聊天区域 - 三层结构 -->
                <div style="flex: 1; display: flex; flex-direction: column; height: 100%; min-width: 0;">
                    <!-- 顶部文档选择区域 - 固定 -->
                    <div v-if="availableDocuments.length" class="document-selection-area" style="flex-shrink: 0; margin-bottom: 15px; padding: 12px; background: #f8f6f2; border-radius: 8px; border: 1px solid #e8dfc8;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="color: #8b7355; font-weight: bold; font-size: 14px;">选择文档:</span>
                            <el-select
                                v-model="selectedDocumentId"
                                placeholder="请选择文档"
                                style="flex: 1; max-width: 300px;"
                                size="small"
                                @change="onDocumentSelectChange">
                                <el-option
                                    v-for="doc in availableDocuments"
                                    :key="doc.id"
                                    :label="doc.title"
                                    :value="doc.id">
                                    <span style="float: left">{{ doc.title }}</span>
                                    <span style="float: right; color: #8492a6; font-size: 13px">{{ doc.file_type }}</span>
                                </el-option>
                            </el-select>
                            <el-button
                                v-if="selectedDocumentId"
                                @click="deleteSelectedDocument"
                                type="text"
                                style="color: #f56c6c;"
                                size="mini">
                                <i class="el-icon-delete"></i>
                            </el-button>
                        </div>
                    </div>

                    <!-- 中间聊天消息区域 - 可滚动 -->
                    <div class="message-list-container" style="flex: 1; overflow: hidden; background-color: rgba(255,255,255,0.5); border-radius: 12px; margin-bottom: 15px;">
                        <div class="message-list" style="height: 100%; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 18px;">
                            <div
                                v-for="(message, index) in messages"
                                :key="index"
                                :class="['message-bubble', message.isUser ? 'user-message' : 'ai-message']">
                                <div class="message-content" v-html="markdownToHtml(message.text)"></div>
                                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                            </div>
                            <!-- AI处理中提示 -->
                            <div v-if="isWaitingForAI" class="message-bubble ai-message">
                                <div class="message-content">
                                    <span class="ai-loading">
                                        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                                    </span>
                                    <span style="margin-left: 10px;">正在思考中...</span>
                                </div>
                                <div class="message-time">问泉</div>
                            </div>
                        </div>
                    </div>

                    <!-- 底部输入区域 - 固定 -->
                    <div class="input-area-container" style="flex-shrink: 0;">
                        <div class="input-area" style="display: flex; gap: 10px; align-items: flex-end; padding: 15px; background: rgba(255,255,255,0.8); border-radius: 12px; border: 1px solid rgba(139, 115, 85, 0.1);">
                            <el-input
                                type="textarea"
                                :rows="1"
                                placeholder="输入你的问题..."
                                v-model="inputMessage"
                                @keyup.enter.native="sendMessage"
                                resize="none"
                                style="flex: 1; border-radius: 24px;">
                            </el-input>

                            <!-- 文档管理按钮组 -->
                            <div style="display: flex; gap: 8px;">
                                <el-button
                                    type="default"
                                    style="background: linear-gradient(135deg, #f5f1e8 0%, #e8dfc8 100%); border: none; border-radius: 24px; padding: 12px; font-weight: 500; box-shadow: 0 2px 6px rgba(139, 115, 85, 0.15); transition: all 0.3s ease; height: 48px; color: #8b7355;"
                                    @click="triggerFileInput"
                                    title="上传文档">
                                    <i class="el-icon-folder-add" style="font-size: 18px;"></i>
                                </el-button>

                                <el-button
                                    type="primary"
                                    style="background: linear-gradient(135deg, #8b7355 0%, #a0866b 100%);
                                           border: none;
                                           border-radius: 24px;
                                           padding: 12px 24px;
                                           font-weight: 500;
                                           letter-spacing: 1px;
                                           box-shadow: 0 2px 6px rgba(139, 115, 85, 0.3);
                                           transition: all 0.3s ease;
                                           height: 48px;"
                                    @click="sendMessage"
                                    :disabled="!inputMessage.trim()"
                                    class="send-button">
                                    <i class="el-icon-s-promotion" style="margin-right: 6px"></i>
                                    发送
                                </el-button>
                            </div>
                        </div>

                        <!-- 文件上传状态提示 -->
                        <div v-if="selectedFileName" style="margin-top: 8px; color: #8b7355; font-size: 14px; text-align: center;">
                            <i class="el-icon-document"></i> {{ selectedFileName }}
                        </div>
                    </div>
                </div>
            </div>
        </el-main>

        <!-- 隐藏的文件输入 -->
        <input
            ref="fileInput"
            type="file"
            style="display: none;"
            @change="handleFileChange"
        />
    </el-container>
    </el-container>
</template>

<style>
    .el-header {
        background-color: #B3C0D1;
        color: #333;
        line-height: 60px;
    }
    
    .el-aside {
        color: #333;
    }
    
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
    
    /* 移除旧的chat-container样式，使用新的布局 */

    .message-list {
        scrollbar-width: thin;
        scrollbar-color: #8b7355 #f0e6d2;
    }
    
    .message-list::-webkit-scrollbar {
        width: 6px;
    }
    
    .message-list::-webkit-scrollbar-thumb {
        background-color: #8b7355;
        border-radius: 3px;
    }
    
    .message-list::-webkit-scrollbar-track {
        background-color: #f0e6d2;
    }
    
    .message-bubble {
        max-width: 80%;
        padding: 22px 28px; /* 增大留白 */
        border-radius: 14px;
        position: relative;
        word-break: break-word;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        font-family: 'Georgia', serif;
        transition: all 0.3s ease;
    }
    
    .message-bubble:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .user-message {
        align-self: flex-end;
        background: linear-gradient(135deg, #e8d5c0 0%, #f5e1c8 100%);
        color: #5a4a3a;
        margin-left: 20%;
    }
    
    .ai-message {
        align-self: flex-start;
        background: linear-gradient(135deg, #e8dfc8 0%, #f5f1e8 100%);
        color: #5a4a3a;
        margin-right: 20%;
        border: 1px solid rgba(139, 115, 85, 0.2);
    }
    
    .message-content {
        margin-bottom: 5px;
        line-height: 1.6;
        font-size: 15px;
    }
    
    .message-time {
        font-size: 12px;
        color: #8b7355;
        text-align: right;
    }
    
    .input-area {
        margin-bottom: 20px;
    }
    
    .el-textarea__inner {
        background-color: #fffdf9;
        border-color: #d4c9a8;
        color: #5a4a3a;
        font-family: 'Georgia', serif;
        border-radius: 24px !important;
        padding: 12px 20px !important;
        line-height: 1.6;
        min-height: 48px !important;
    }

    /* 发送按钮悬浮效果 */
    .send-button:not(:disabled):hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(139, 115, 85, 0.4);
        background: linear-gradient(135deg, #9d8266 0%, #b4967a 100%);
    }
    
    .send-button:not(:disabled):active {
        transform: scale(0.98);
    }

    /* 删除了打字动画相关的CSS */

    .ai-loading {
      display: inline-block;
      min-width: 36px;
      height: 22px;
      vertical-align: middle;
    }
    .ai-loading .dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin: 0 2px;
      background: #8b7355;
      border-radius: 50%;
      animation: ai-bounce 1.2s infinite both;
    }
    .ai-loading .dot:nth-child(2) {
      animation-delay: 0.2s;
    }
    .ai-loading .dot:nth-child(3) {
      animation-delay: 0.4s;
    }
    @keyframes ai-bounce {
      0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
      40% { transform: scale(1.2); opacity: 1; }
    }

    /* 侧边栏面板样式 */
    .sidebar-panel {
        height: 100%;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .panel-header {
        padding: 16px 20px;
        border-bottom: 1px solid #f0f0f0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #f8f6f2 0%, #f5f1e8 100%);
    }

    .header-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: #5a4a3a;
        font-size: 15px;
    }

    .header-title i {
        color: #8b7355;
        font-size: 16px;
    }



    .header-actions {
        display: flex;
        gap: 4px;
    }

    .action-btn {
        padding: 6px !important;
        color: #8b7355 !important;
        border-radius: 6px !important;
        transition: all 0.3s ease !important;
    }

    .action-btn:hover {
        background: rgba(139, 115, 85, 0.1) !important;
        color: #6d5a47 !important;
    }

    .action-btn.danger {
        color: #f56c6c !important;
    }

    .action-btn.danger:hover {
        background: rgba(245, 108, 108, 0.1) !important;
        color: #e6393f !important;
    }

    .panel-content {
        flex: 1;
        padding: 16px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: #d4c5a9 transparent;
    }

    .panel-content::-webkit-scrollbar {
        width: 4px;
    }

    .panel-content::-webkit-scrollbar-thumb {
        background-color: #d4c5a9;
        border-radius: 2px;
    }

    .panel-content::-webkit-scrollbar-track {
        background: transparent;
    }

    /* 聊天历史样式 */
    .history-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .history-item {
        padding: 12px;
        border-radius: 8px;
        background: #f8f6f2;
        border: 1px solid #e8dfc8;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: flex-start;
        gap: 8px;
        position: relative;
    }

    .history-item:hover {
        background: #f0ede6;
        border-color: #d4c5a9;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(139, 115, 85, 0.1);
    }

    .history-item:hover .history-actions {
        opacity: 1;
    }

    .history-item.active {
        background: #e8dfc8;
        border-color: #8b7355;
        box-shadow: 0 2px 8px rgba(139, 115, 85, 0.2);
    }

    .history-content {
        flex: 1;
        min-width: 0;
    }

    .history-preview {
        font-size: 14px;
        color: #5a4a3a;
        line-height: 1.4;
        margin-bottom: 6px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-weight: 500;
    }



    .history-actions {
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .delete-session-btn {
        padding: 4px !important;
        color: #f56c6c !important;
        border-radius: 4px !important;
    }

    .delete-session-btn:hover {
        background: rgba(245, 108, 108, 0.1) !important;
    }



    /* 空状态样式 */
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        color: #8b7355;
    }

    .empty-state i {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
    }

    .empty-state p {
        margin: 0 0 16px 0;
        font-size: 14px;
        color: #999;
    }

    .start-chat-btn, .upload-btn {
        color: #8b7355 !important;
        font-weight: 500 !important;
    }

    .start-chat-btn:hover, .upload-btn:hover {
        color: #6d5a47 !important;
    }

    /* 响应式布局调整 */
    @media (max-width: 1200px) {
        .el-col-5 {
            display: none !important;
        }

        .el-col-19 {
            width: 100% !important;
            flex: 0 0 100% !important;
            max-width: 100% !important;
        }
    }

    @media (max-width: 768px) {
        .input-area {
            flex-direction: column !important;
            gap: 10px !important;
        }

        .input-area > div {
            width: 100% !important;
            justify-content: center !important;
        }
    }
</style>

<script>
import axios from 'axios';
import { Marked } from 'marked'
import { markedHighlight } from "marked-highlight";
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import python from 'highlight.js/lib/languages/python';
import java from 'highlight.js/lib/languages/java';
import xml from 'highlight.js/lib/languages/xml';
import json from 'highlight.js/lib/languages/json';
import css from 'highlight.js/lib/languages/css';
import markdown from 'highlight.js/lib/languages/markdown';
import bash from 'highlight.js/lib/languages/bash';
import 'highlight.js/styles/github.css'; // 推荐风格，可换为其它

// 注册常用语言
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('java', java);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('json', json);
hljs.registerLanguage('css', css);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('bash', bash);

export default {
    data() {
        return {
            // 消息相关
            inputMessage: '',
            messages: [],
            isWaitingForAI: false,

            // 会话相关
            currentSessionId: null,
            currentConversationId: null,
            chatHistory: [],

            // 文档相关
            selectedFile: null,
            selectedFileName: '',
            availableDocuments: [],
            selectedDocumentId: null,

            // 状态相关
            pollingTimer: null,
            isLoading: false,
            username: '',
            userInitial: '',

            // API相关
            form: {
                message: '',
                timestamp: null,
                document_id: null,
                conversation_id: null,
                username: ''
            }
        }
    },
    computed: {
        HOST() {
            return 'http://localhost:8000/api';
        },
        url() {
            return `${this.HOST}/chat/`;
        }
    },
    created() {
        // 检查localStorage中是否有用户信息
        const userInfo = localStorage.getItem('userInfo');
        // 将JSON字符串转换为对象
        const parsedUserInfo = JSON.parse(userInfo);
        // 触发Vuex action来更新store中的用户信息
        this.$store.dispatch('restoreUserInfo', parsedUserInfo);

        // 页面加载时从store恢复历史
        const history = this.$store.getters.getChatHistory;
        if (history && Array.isArray(history) && history.length > 0) {
            this.messages = history.map(msg => ({...msg, timestamp: new Date(msg.timestamp)}));
        }

        // 获取当前用户信息
        const user = this.$store.getters.getUserInfo;
        if (user && user.username) {
            this.username = user.username;
            this.userInitial = user.username.charAt(0).toUpperCase();
        } else {
            this.username = '未登录';
            this.userInitial = '?';
        }

        // 获取可用文档列表
        this.loadAvailableDocuments();

        // 获取聊天历史
        this.loadChatHistory();

        
        //从localStorage恢复当前项目信息，仅同步id和name到store
        const currentProjectStr = localStorage.getItem('currentProject');
        //let projectId = null;
        if (currentProjectStr) {
            try {
                const currentProject = JSON.parse(currentProjectStr);
                if (currentProject && currentProject.id && currentProject.name) {
                    this.$store.dispatch('setCurrentProject', {
                        id: currentProject.id,
                        name: currentProject.name
                    });
                    //projectId = currentProject.id;
                }
            } catch (e) {
                // ignore
            }
        }

    },

    mounted() {
        // 页面初次渲染后自动滚动到底部
        this.$nextTick(() => {
            const container = document.querySelector('.message-list');
            if (container) container.scrollTop = container.scrollHeight;
        });
    },

    beforeDestroy() {
        // 组件销毁前清理轮询
        this.stopPolling();
    },

    watch: {
        messages: {
            handler(newVal) {
                // 每次对话变更都保存到store
                this.$store.dispatch('updateChatHistory', newVal.map(msg => ({
                    ...msg,
                    timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp
                })));
            },
            deep: true
        }
    },
    methods: {
        // 统一的API调用方法
        async apiCall(method, url, data = null, config = {}) {
            try {
                const response = await axios[method](url, data, config);
                return response;
            } catch (error) {
                console.error(`API调用失败 [${method.toUpperCase()}] ${url}:`, error);
                throw error;
            }
        },

        // 获取当前用户名
        getCurrentUsername() {
            const user = this.$store.getters.getUserInfo;
            return user && user.username ? user.username : '未登录';
        },

        markdownToHtml(message) {
            if (!message) return '';
            const marked = new Marked(
                markedHighlight({
                    pedantic: false,
                    gfm: true,
                    breaks: true,
                    smartLists: true,
                    xhtml: true,
                    async: false,
                    langPrefix: 'hljs language-',
                    emptyLangClass: 'no-lang',
                    highlight: (code, lang) => {
                        if (lang && hljs.getLanguage(lang)) {
                            return hljs.highlight(code, { language: lang }).value;
                        }
                        return hljs.highlightAuto(code).value;
                    }
                })
            );
            return marked.parse(message);
        },
        async sendMessage() {
            if (this.inputMessage.trim() === '') return;

            // 准备发送数据
            const sendData = {
                message: this.inputMessage,
                username: this.getCurrentUsername(),
                conversation_id: this.currentConversationId,
                document_id: this.selectedDocumentId || null
            };

            // 添加用户消息到界面
            const userMsg = {
                text: this.inputMessage,
                isUser: true,
                timestamp: new Date()
            };
            this.messages.push(userMsg);

            // 同步到store
            this.$store.dispatch('addChatMessage', {
                ...userMsg,
                timestamp: userMsg.timestamp.toISOString()
            });

            // 清空输入框并滚动到底部
            this.inputMessage = '';
            this.$nextTick(() => {
                const container = document.querySelector('.message-list');
                if (container) container.scrollTop = container.scrollHeight;
            });

            // 显示等待状态
            this.isWaitingForAI = true;

            try {
                // 发送消息到后端API（同步处理）
                const response = await axios.post(this.url, sendData);
                console.log('消息发送成功:', response.data);

                // 保存会话信息
                if (response.data.conversation_id) {
                    this.currentConversationId = response.data.conversation_id;
                }

                // 直接添加AI回复（不需要轮询）
                if (response.data.ai_response) {
                    const aiMsg = {
                        text: response.data.ai_response,
                        isUser: false,
                        timestamp: new Date()
                    };
                    this.messages.push(aiMsg);

                    // 同步到store
                    this.$store.dispatch('addChatMessage', {
                        ...aiMsg,
                        timestamp: aiMsg.timestamp.toISOString()
                    });

                    this.$nextTick(() => {
                        const container = document.querySelector('.message-list');
                        if (container) container.scrollTop = container.scrollHeight;
                    });
                }

                // 重新加载聊天历史（确保新对话出现在历史列表中）
                this.loadChatHistory();

                this.isWaitingForAI = false;

            } catch (error) {
                console.error('发送失败:', error);
                this.$message.error('发送失败：' + (error.response?.data?.error || error.message));
                this.isWaitingForAI = false;
            }
        },
        startPolling() {
            if (this.pollingTimer) {
                clearInterval(this.pollingTimer);
            }

            this.pollingTimer = setInterval(() => {
                this.checkMessageStatus();
            }, 1000); // 每秒检查一次
        },

        checkMessageStatus() {
            if (!this.currentSessionId) return;

            axios.get(`${this.HOST}/chat/status/${this.currentSessionId}/`)
                .then(response => {
                    console.log('状态检查:', response.data);

                    if (response.data.is_ready) {
                        // 消息已完成
                        this.stopPolling();
                        this.isWaitingForAI = false;

                        // 添加AI回复到消息列表
                        const aiMsg = {
                            text: response.data.ai_response,
                            isUser: false,
                            timestamp: new Date()
                        };
                        this.messages.push(aiMsg);

                        // 同步到store
                        this.$store.dispatch('addChatMessage', {
                            ...aiMsg,
                            timestamp: aiMsg.timestamp.toISOString()
                        });

                        this.$nextTick(() => {
                            const container = document.querySelector('.message-list');
                            if (container) container.scrollTop = container.scrollHeight;
                        });

                        this.currentSessionId = null;
                    }
                })
                .catch(error => {
                    console.error('状态检查失败:', error);
                    // 继续轮询，不中断
                });
        },

        stopPolling() {
            if (this.pollingTimer) {
                clearInterval(this.pollingTimer);
                this.pollingTimer = null;
            }
        },
        formatTime(date) {
            return `${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
        },
        gotoSummarize() {
            this.$router.push({ path: '/summarize' });
        },
        gotoTest() {
            this.$router.push({ path: '/test' });
        },
        gotoPrj(){
            this.$router.push({ path: '/project' });
        },
        triggerFileInput() {
            this.$refs.fileInput.click();
        },
        async handleFileChange(event) {
            const file = event.target.files[0];
            if (file) {
                this.selectedFile = file;
                this.selectedFileName = file.name;

                // 自动上传文件
                await this.uploadDocument();
            } else {
                this.selectedFile = null;
                this.selectedFileName = '';
                this.currentDocumentId = null;
            }
        },
        async uploadDocument() {
            if (!this.selectedFile) return;

            const formData = new FormData();
            formData.append('file', this.selectedFile);

            try {
                this.isLoading = true;
                const response = await axios.post(this.HOST + '/chat/upload/', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });

                if (response.data.document_id) {
                    this.currentDocumentId = response.data.document_id;

                    // 添加系统消息到聊天记录
                    const systemMsg = {
                        text: `📄 文档 "${response.data.filename}" 上传成功！现在您可以基于这个文档进行问答。`,
                        isUser: false,
                        timestamp: new Date(),
                        isSystem: true
                    };

                    this.messages.push(systemMsg);

                    // 同步到store
                    this.$store.dispatch('addChatMessage', {
                        ...systemMsg,
                        timestamp: systemMsg.timestamp.toISOString()
                    });

                    this.$nextTick(() => {
                        const container = document.querySelector('.message-list');
                        if (container) container.scrollTop = container.scrollHeight;
                    });

                    this.$message.success(`文档 "${response.data.filename}" 上传成功！`);

                    // 重新加载文档列表
                    this.loadAvailableDocuments();
                } else {
                    throw new Error('文档上传失败');
                }
            } catch (error) {
                console.error('文档上传失败:', error);

                const errorMsg = {
                    text: `❌ 文档上传失败: ${error.response?.data?.error || error.message}`,
                    isUser: false,
                    timestamp: new Date(),
                    isSystem: true
                };

                this.messages.push(errorMsg);

                this.$message.error(`文档上传失败: ${error.response?.data?.error || error.message}`);

                this.selectedFile = null;
                this.selectedFileName = '';
                this.currentDocumentId = null;
            } finally {
                this.isLoading = false;
            }
        },

        // 新增：加载可用文档列表
        async loadAvailableDocuments() {
            try {
                const response = await this.apiCall('get', `${this.HOST}/chat/documents/`);
                if (response.data && response.data.documents) {
                    this.availableDocuments = response.data.documents;
                    console.log('加载文档列表成功:', this.availableDocuments);
                }
            } catch (error) {
                this.$message.error('加载文档列表失败: ' + (error.response?.data?.error || error.message));
            }
        },

        // 新增：删除选中的文档
        deleteSelectedDocument() {
            if (!this.selectedDocumentId) return;

            const selectedDoc = this.availableDocuments.find(doc => doc.id === this.selectedDocumentId);
            if (!selectedDoc) return;

            this.$confirm(`确定要删除文档"${selectedDoc.title}"吗？此操作不可恢复！`, '警告', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const response = await this.apiCall('delete', `${this.HOST}/chat/documents/${selectedDoc.id}/delete/`);

                    if (response.status === 200) {
                        this.$message.success(`文档 "${selectedDoc.title}" 删除成功`);

                        // 清空选择
                        this.selectedDocumentId = null;

                        // 重新加载文档列表
                        await this.loadAvailableDocuments();
                    }
                } catch (error) {
                    console.error('删除文档失败:', error);
                    this.$message.error(`删除失败: ${error.response?.data?.error || error.message}`);
                }
            }).catch(() => {
                this.$message.info('已取消删除');
            });
        },



        // 新增：文档下拉选择变化
        onDocumentSelectChange(documentId) {
            const selectedDoc = this.availableDocuments.find(doc => doc.id === documentId);
            if (selectedDoc) {
                console.log('选择文档:', selectedDoc.title, 'ID:', documentId);
            }
        },

        // 新增：格式化文件大小
        formatFileSize(bytes) {
            if (!bytes) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        // 新增：加载聊天历史
        async loadChatHistory() {
            try {
                const username = this.getCurrentUsername();
                const url = `${this.HOST}/chat/conversations/?username=${encodeURIComponent(username)}`;
                const response = await fetch(url);

                if (response.ok) {
                    const data = await response.json();
                    if (data && data.conversations) {
                        // 过滤掉没有消息的空对话
                        const validConversations = data.conversations.filter(conv =>
                            conv.message_count > 0 && conv.title !== '新对话'
                        );

                        this.chatHistory = validConversations.map(conv => ({
                            id: conv.id,
                            user_message: conv.title,
                            timestamp: new Date(conv.updated_at),
                            messages: [],
                            message_count: conv.message_count
                        }));
                        return;
                    }
                }
                this.chatHistory = [];
            } catch (error) {
                this.chatHistory = [];
            }
        },

        // 新增：分组聊天历史
        groupChatHistory(messages) {
            const sessions = [];
            let currentSession = null;

            messages.forEach(msg => {
                if (msg.isUser) {
                    // 用户消息开始新的会话
                    currentSession = {
                        id: Date.now() + Math.random(),
                        user_message: msg.text,
                        timestamp: new Date(msg.timestamp),
                        messages: [msg]
                    };
                    sessions.push(currentSession);
                } else if (currentSession) {
                    // AI回复添加到当前会话
                    currentSession.messages.push(msg);
                }
            });

            return sessions.reverse(); // 最新的在前面
        },

        // 新增：加载聊天会话
        async loadChatSession(session) {
            try {
                const response = await this.apiCall('get', `${this.HOST}/chat/conversations/${session.id}/`);

                if (response.data && response.data.messages) {
                    this.messages = response.data.messages.map(msg => ({
                        text: msg.content,
                        isUser: msg.is_user,
                        timestamp: new Date(msg.created_at),
                        documentId: msg.document_id,
                        documentTitle: msg.document_title
                    }));

                    this.currentConversationId = session.id;

                    this.$nextTick(() => {
                        const container = document.querySelector('.message-list');
                        if (container) container.scrollTop = container.scrollHeight;
                    });
                }
            } catch (error) {
                this.$message.error('加载对话失败');
                if (session.messages && session.messages.length > 0) {
                    this.messages = session.messages.map(msg => ({
                        ...msg,
                        timestamp: new Date(msg.timestamp)
                    }));
                    this.currentSessionId = session.id;
                }
            }
        },

        // 新增：清空聊天历史
        async clearChatHistory() {
            this.$confirm('确定要清空所有聊天历史吗？此操作不可恢复！', '警告', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const response = await this.apiCall('delete', `${this.HOST}/chat/conversations/clear/`, {
                        username: this.getCurrentUsername()
                    });

                    if (response.status === 200) {
                        // 清空前端显示
                        this.chatHistory = [];
                        this.messages = [];
                        this.currentConversationId = null;

                        // 清空store中的历史记录
                        this.$store.dispatch('clearChatHistory');

                        this.$message.success(`聊天历史已清空，共删除 ${response.data.deleted_count} 个对话`);
                    }
                } catch (error) {
                    console.error('清空聊天历史失败:', error);
                    this.$message.error('清空失败: ' + (error.response?.data?.error || error.message));
                }
            }).catch(() => {
                this.$message.info('已取消清空');
            });
        },

        // 新增：获取会话标题（取第一个问题的前30个字符）
        getSessionTitle(session) {
            if (session.user_message && session.user_message.trim()) {
                const title = session.user_message.trim();
                return title.length > 30 ? title.substring(0, 30) + '...' : title;
            }
            return '新对话';
        },

        // 新增：格式化历史时间
        formatHistoryTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            if (diff < 60000) { // 1分钟内
                return '刚刚';
            } else if (diff < 3600000) { // 1小时内
                return Math.floor(diff / 60000) + '分钟前';
            } else if (diff < 86400000) { // 1天内
                return Math.floor(diff / 3600000) + '小时前';
            } else {
                return date.toLocaleDateString();
            }
        },

        // 新增：开始新对话
        startNewChat() {
            // 清空当前聊天状态，开始新对话
            this.messages = [];
            this.currentSessionId = null;
            this.currentConversationId = null;
            this.selectedDocumentId = null;
            this.$message.success('已开始新对话');
        },

        // 新增：删除会话
        deleteSession(session) {
            this.$confirm(`确定要删除这个对话吗？`, '确认删除', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const url = `${this.HOST}/chat/conversations/${session.id}/`;
                    const response = await fetch(url, { method: 'DELETE' });

                    if (response.ok) {
                        this.chatHistory = this.chatHistory.filter(s => s.id !== session.id);
                        if (this.currentConversationId === session.id) {
                            this.messages = [];
                            this.currentConversationId = null;
                        }
                        this.$message.success('对话已删除');
                    } else {
                        this.$message.error('删除失败');
                    }
                } catch (error) {
                    this.$message.error('删除失败');
                }
            }).catch(() => {
                this.$message.info('已取消删除');
            });
        },

        // 新增：删除文档（优化版）
        deleteDocument(doc) {
            this.$confirm(`确定要删除文档"${doc.title}"吗？此操作不可恢复！`, '警告', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(async () => {
                try {
                    const response = await this.apiCall('delete', `${this.HOST}/chat/documents/${doc.id}/delete/`);

                    if (response.status === 200) {
                        this.$message.success(`文档 "${doc.title}" 删除成功`);

                        // 如果删除的是当前选中的文档，清空选择
                        if (this.selectedDocumentId === doc.id) {
                            this.selectedDocumentId = null;
                        }

                        // 重新加载文档列表
                        await this.loadAvailableDocuments();
                    }
                } catch (error) {
                    console.error('删除文档失败:', error);
                    this.$message.error(`删除失败: ${error.response?.data?.error || error.message}`);
                }
            }).catch(() => {
                this.$message.info('已取消删除');
            });
        }
    }
};
</script>