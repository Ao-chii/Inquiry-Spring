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
    </el-aside>
    
    <el-container>
        <el-main style="padding: 20px; display: flex; flex-direction: column; height: 100%; background-color: rgba(255,255,255,0.7); border-radius: 16px; margin: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid rgba(139, 115, 85, 0.1)">
            <div class="chat-container">
                <div class="message-list">
                    <div 
                        v-for="(message, index) in messages" 
                        :key="index" 
                        :class="['message-bubble', message.isUser ? 'user-message' : 'ai-message']">
                        <div class="message-content" v-html="markdownToHtml(message.text)"></div>
                        <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                    </div>
                    <!-- AI动画气泡 -->
                    <div v-if="aiTyping" class="message-bubble ai-message">
                        <div class="message-content">
                            <template v-if="aiTypingLines.length > 0">
                                <div v-html="aiTypingHtml"></div>
                            </template>
                            <template v-else>
                                <span class="ai-loading">
                                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                                </span>
                            </template>
                        </div>
                        <div class="message-time">问泉</div>
                    </div>
                </div>
                <div class="input-area" style="display: flex; gap: 10px; align-items: center;">
                    <el-input 
                        type="textarea" 
                        :rows="1" 
                        placeholder="输入你的问题..."
                        v-model="inputMessage"
                        @keyup.enter.native="sendMessage"
                        resize="none"
                        style="flex: 1; border-radius: 24px; padding: 12px 20px;">
                    </el-input>
                    <el-button
                        type="default"
                        style="background: linear-gradient(135deg, #f5f1e8 0%, #e8dfc8 100%); border: none; border-radius: 24px; padding: 12px 24px; font-weight: 500; letter-spacing: 1px; box-shadow: 0 2px 6px rgba(139, 115, 85, 0.15); transition: all 0.3s ease; height: 48px; color: #8b7355; min-width: 90px; font-size: 15px; margin-left: 0; display: flex; align-items: center; justify-content: center;"
                        @click="triggerFileInput"
                    >
                        <i class="el-icon-folder-add" style="font-size: 26px; vertical-align: middle; display: flex; align-items: center; justify-content: center; width: 100%;"></i>
                    </el-button>
                    <input
                        ref="fileInput"
                        type="file"
                        style="display: none;"
                        @change="handleFileChange"
                    />
                    <span v-if="selectedFileName" style="color: #8b7355; font-size: 14px; margin-left: 4px; margin-right: 8px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-block;">{{ selectedFileName }}</span>
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
        </el-main>
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
    
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        padding: 25px;
        background-color: rgba(255,255,255,0.7);
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid rgba(139, 115, 85, 0.1);
    }
    
    .message-list {
        flex: 1;
        overflow-y: auto;
        margin-bottom: 20px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 18px;
        background-color: rgba(255,255,255,0.5);
        border-radius: 12px;
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

    .typing-cursor {
      display: inline-block;
      width: 1ch;
      animation: blink 1s steps(1) infinite;
      color: #8b7355;
    }
    @keyframes blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0; }
    }

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
            url: this.HOST + '/chat/',
            inputMessage: '',
            messages: [],
            form: {
                message: '',
                timestamp: ''
            },
            aiTyping: false,
            aiDisplayLines: [], // AI动画用
            aiCurrentLineText: '',
            aiTypingTimer: null,
            aiTypingLineIdx: 0,
            aiTypingCharIdx: 0,
            aiTypingLines: [],
            selectedFile: null,
            selectedFileName: '', // 新增：存储选中文件名
            currentDocumentId: null, // 当前文档ID
            isLoading: false // 加载状态
        }
    },
    created() {
        // 页面加载时从store恢复历史
        const history = this.$store.getters.getChatHistory;
        if (history && Array.isArray(history) && history.length > 0) {
            this.messages = history.map(msg => ({...msg, timestamp: new Date(msg.timestamp)}));
        }
    },
    mounted() {
        // 页面初次渲染后自动滚动到底部
        this.$nextTick(() => {
            const container = document.querySelector('.message-list');
            if (container) container.scrollTop = container.scrollHeight;
        });
    },
    computed: {
        aiTypingHtml() {
            let arr = this.aiDisplayLines.slice();
            if (this.aiCurrentLineText) {
                arr.push(this.aiCurrentLineText + '<span class="typing-cursor">|</span>');
            }
            return this.markdownToHtml(arr.join('\n'));
        }
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
        sendMessage() {
            if (this.inputMessage.trim() === '') return;
            this.form.message = this.inputMessage;
            this.form.timestamp = new Date();
            // 添加用户消息
            const userMsg = {
                text: this.inputMessage,
                isUser: true,
                timestamp: this.form.timestamp
            };
            this.messages.push(userMsg);
            // 同步到store
            this.$store.dispatch('addChatMessage', {
                ...userMsg,
                timestamp: userMsg.timestamp.toISOString()
            });
            this.inputMessage = '';
            this.$nextTick(() => {
                const container = document.querySelector('.message-list');
                if (container) container.scrollTop = container.scrollHeight;
            });
            // 发送消息到后端API
            axios.post(this.url, this.form).then((response) => {
                console.log('消息发送成功:', response.data);
                // 不直接push AI消息，走动画
            })
            .catch(error => {
                console.error('发送失败:', error);
                this.$message.error('发送失败：' + error.message);
                this.aiTyping = false; // 发送失败时停止AI动画
            });
            // 显示AI加载动画
            this.aiTyping = true;
            this.aiDisplayLines = [];
            this.aiCurrentLineText = '';
            this.aiTypingLineIdx = 0;
            this.aiTypingCharIdx = 0;
            this.aiTypingLines = [];
            // 获取AI回复（减少延迟时间）
            setTimeout(() => {
                axios.get(this.url).then(response => {
                    console.log('AI回复数据:', response.data); // 调试日志
                    const aiMessage = response.data.ai_response || response.data.AIMessage || 'AI未返回内容';
                    this.startAiTypingAnimation(aiMessage);
                })
                .catch(error => {
                    console.error('获取AI回复失败:', error); // 调试日志
                    this.$message.error('获取AI回复失败:' + error.message);
                    this.aiTyping = false;
                });
            }, 10000); // 从20秒减少到1秒
        },
        startAiTypingAnimation(aiText) {
            if (this.aiTypingTimer) {
                clearTimeout(this.aiTypingTimer);
                this.aiTypingTimer = null;
            }
            this.aiTyping = true;
            this.aiDisplayLines = [];
            this.aiCurrentLineText = '';
            this.aiTypingLineIdx = 0;
            this.aiTypingCharIdx = 0;
            this.aiTypingLines = aiText.split(/\r?\n/);
            this.typeAiNextChar();
        },
        typeAiNextChar() {
            if (this.aiTypingLineIdx >= this.aiTypingLines.length) {
                this.aiCurrentLineText = '';
                this.aiTyping = false;
                // 动画结束后将AI消息push到messages
                const aiMsg = {
                    text: this.aiTypingLines.join('\n'),
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
                return;
            }
            const line = this.aiTypingLines[this.aiTypingLineIdx];
            if (this.aiTypingCharIdx < line.length) {
                this.aiCurrentLineText += line[this.aiTypingCharIdx];
                this.aiTypingCharIdx++;
                this.aiTypingTimer = setTimeout(this.typeAiNextChar, 28);
            } else {
                this.aiDisplayLines.push(this.aiCurrentLineText);
                this.aiCurrentLineText = '';
                this.aiTypingLineIdx++;
                this.aiTypingCharIdx = 0;
                this.aiTypingTimer = setTimeout(this.typeAiNextChar, 180);
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
        }
    }
};
</script>