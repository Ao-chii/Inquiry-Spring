<template>
    <el-container style="height: 100vh; background: linear-gradient(135deg, #f5f1e8 0%, #f0e6d2 100%)">
    <el-aside width="240px" style="background: linear-gradient(to bottom, #e8dfc8, #d8cfb8); border-right: 1px solid #d4c9a8; border-radius: 0 12px 12px 0; box-shadow: 2px 0 10px rgba(0,0,0,0.1); overflow-x: hidden">
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
            :default-active="'1'"
            style="overflow-x: hidden">
            <el-menu-item @click="gotoChat" index="2" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px)">
                <i class="el-icon-chat-dot-round"></i>
                <span>智能答疑</span>
            </el-menu-item>
            <el-menu-item index="1" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px); background: linear-gradient(135deg, #5a4a3a 0%, #3a2e24 100%); color: white; box-shadow: 0 2px 8px rgba(90, 74, 58, 0.3)">
                <i class="el-icon-notebook-2" style="color: white"></i>
                <span>智慧总结</span>
            </el-menu-item>
            <el-menu-item @click="gotoTest" index="3" style="border-radius: 8px; margin: 8px; width: calc(100% - 16px); transition: all 0.3s">
                <i class="el-icon-edit" style="color: #8b7355"></i>
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
    
    <el-container>
        <el-main style="padding: 10px; display: flex; flex-direction: column; height: 100%; background-color: rgba(255,255,255,0.7); border-radius: 16px; margin: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid rgba(139, 115, 85, 0.1)">
            <div class="content-container" style="margin: 10px; padding: 0; background: transparent; box-shadow: none; border: none">
                <el-row :gutter="20" style="height: 100%">
                    <el-col :span="7.5" style="padding: 10px;">
                        <div style="width: 400px; height: 100%; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); display: flex; flex-direction: column;">
                            <h3 style="margin-bottom: 16px; color: #5a4a3a; display: flex; align-items: center; gap: 8px;">
                                选择文件
                                <el-tooltip content="选择您上传的学习材料或学习笔记，生成总结" placement="right">
                                    <i class="el-icon-question" style="color: #8b7355; font-size: 16px;"></i>
                                </el-tooltip>
                            </h3>
                            <div style="flex: 1; display: flex; flex-direction: column;">
                                <!-- <el-upload
                                    class="upload-demo"
                                    show-file-list="false"
                                    drag
                                    :action=this.url
                                    multiple
                                    :on-success="handleUploadSuccess"
                                    :before-upload="beforeUpload"
                                    style="flex: 1; display: flex; flex-direction: column;">
                                    <i class="el-icon-upload" style="color: #8b7355; font-size: 48px; margin-bottom: 16px;"></i>
                                    <div class="el-upload__text" style="color: #5a4a3a; font-size: 14px;">将文件拖到此处，或<em style="color: #8b7355;">点击上传</em></div>
                                    <div class="el-upload__tip" slot="tip" style="color: #8b7355; margin-top: 16px;">支持word,pdf格式</div>
                                </el-upload> -->
                                <!-- 新增：已上传文件表格，单独分区 -->
                                <div v-if="uploadedFiles.length" style="margin: 50px auto 0 auto; padding: 16px 12px; background: #f8f6f2; border-radius: 8px; box-shadow: 0 2px 8px rgba(139,115,85,0.06); border: 1px solid #e8dfc8; width: 95%; max-width: 600px; min-width: 220px; box-sizing: border-box; display: flex; flex-direction: column; align-items: center;">
                                    <div style="font-weight: bold; color: #8b7355; margin-bottom: 10px; font-size: 15px; letter-spacing: 1px; width: 100%; text-align: left;">当前项目文档</div>
                                    <el-table 
                                        :data="uploadedFiles" 
                                        border 
                                        style="width: 100%; background: #fff;"
                                        highlight-current-row
                                        @current-change="handleFileRowSelect"
                                        :current-row="selectedFileRow"
                                    >
                                        <el-table-column prop="name" label="文件名" min-width="120" align="left">
                                            <template slot-scope="scope">
                                                <span :style="scope.row.id === selectedFileId ? 'color: #67c23a;' : 'color: #5a4a3a;'">
                                                    <i class="el-icon-document" style="margin-right: 6px;" :style="scope.row.id === selectedFileId ? 'color: #67c23a;' : 'color: #8b7355;'"></i>{{ scope.row.name }}
                                                </span>
                                            </template>
                                        </el-table-column>
                                        <el-table-column label="选择" width="50">
                                            <template slot-scope="scope">
                                                <el-radio 
                                                    v-model="selectedFileId" 
                                                    :label="scope.row.id"
                                                    @change="() => onFileRadioChange(scope.row)"
                                                >
                                                    <!-- 不显示任何label内容，保持圆圈 -->
                                                    <span style="display:none">{{scope.row.id}}</span>
                                                </el-radio>
                                            </template>
                                        </el-table-column>
                                    </el-table>
                                </div>
                                <v-btn @click="generateSummary" color="#8b7355" style="color: white; margin-top: 20px; align-self: flex-end;">
                                    立即生成
                                </v-btn>
                            </div>
                        </div>
                    </el-col>
                    <el-col :span="16" style="padding: 10px;">
                        <div style="height: 100%; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); display: flex; flex-direction: column;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                                <h3 style="color: #5a4a3a;">总结内容</h3>
                                <v-btn @click="output" color="#8b7355" style="color: white;">
                                    导出
                                </v-btn>
                            </div>
                            <div class="markdown-container" style="flex: 1; overflow-y: auto;">
                                <div v-if="loading" style="display: flex; align-items: center; justify-content: center; height: 100%;">
                                    <span class="ai-loading">
                                        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                                    </span>
                                </div>
                                <div v-else v-html="animatedHtml"></div>
                            </div>
                        </div>
                    </el-col>
                </el-row>
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
    
    .content-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        padding: 25px;
        background-color: rgba(255,255,255,0.7);
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid rgba(139, 115, 85, 0.1);
    }
    
    .markdown-container {
        padding: 15px 20px;
        line-height: 1.6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #5a4a3a;
    }
    
    .markdown-container h1, 
    .markdown-container h2, 
    .markdown-container h3 {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        font-weight: 600;
        color: #5a4a3a;
    }
    
    .markdown-container p {
        margin-bottom: 1em;
    }
    
    /* 强制覆盖所有代码块样式 */
    .markdown-container pre {
        background: #e0e0e0 !important;
        padding: 12px 16px !important;
        border-radius: 6px !important;
        overflow: auto !important;
        margin: 0.5em 0 1.5em 0 !important;
        border: 2px solid #c0c0c0 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15) !important;
    }
    
    /* 覆盖highlight.js生成的元素 */
    .markdown-container pre code.hljs {
        background: transparent !important;
        padding: 0 !important;
        color: inherit !important;
    }
    
    /* 内联代码样式 */
    .markdown-container code:not(pre code) {
        font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
        background: #f6f8fa;
        padding: 2px 4px;
        border-radius: 4px;
        color: #8b7355;
    }

    .markdown-container blockquote {
        border-left: 4px solid #8b7355;
        background: #f8f6f2;
        color: #6a5a3a;
        margin: 1em 0;
        padding: 0.7em 1.2em;
        border-radius: 4px;
        font-style: italic;
    }

    .typing-cursor {
        display: inline-block;
        width: 2px;
        height: 1.2em;
        margin-left: 2px;
        background-color: #8b7355;
        animation: blink 1s step-end infinite;
        vertical-align: middle;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
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



export default {
    data() {
        return {
            summarizeMsg:">tips:\n > - 选择你要总结的文档\n> - 生成总结",
            url:this.HOST+'/summarize/',
            md:'# hhh',
            // 动画相关
            displayLines: [],
            currentLine: "",
            typingTimer: null,
            lineIdx: 0,
            typingLines: [],
            loading: false, // 新增加载动画状态
            uploadedFiles: [], // 已上传文件列表
            selectedFileRow: null, // 当前选中的文件行对象
            selectedFileName: '', // 当前选中文件名
            selectedFileId: null, // 新增：当前选中的文件id（用于单选）
            username: '',
            userInitial: '',
            currentPrjId: null, // 新增：当前项目的id
        }
    },
    created() {
        // 检查localStorage中是否有用户信息
        const userInfo = localStorage.getItem('userInfo');
        // 将JSON字符串转换为对象
        const parsedUserInfo = JSON.parse(userInfo);
        // 触发Vuex action来更新store中的用户信息
        this.$store.dispatch('restoreUserInfo', parsedUserInfo);

        // 获取当前用户信息
        const user = this.$store.getters.getUserInfo;
        if (user && user.username) {
            this.username = user.username;
            this.userInitial = user.username.charAt(0).toUpperCase();
        } else {
            this.username = '未登录';
            this.userInitial = '?';
        }

        // 新增：从localStorage恢复当前项目信息，仅同步id和name到store
        const currentProjectStr = localStorage.getItem('currentProject');
        let projectId = null;
        if (currentProjectStr) {
            try {
                const currentProject = JSON.parse(currentProjectStr);
                if (currentProject && currentProject.id && currentProject.name) {
                    this.$store.dispatch('setCurrentProject', {
                        id: currentProject.id,
                        name: currentProject.name
                    });
                    projectId = currentProject.id;
                    this.currentPrjId=projectId;
                }
            } catch (e) {
                // ignore
            }
        }

        // 新增：页面创建时自动请求后端获取当前项目文档列表
        if (projectId && this.username && this.username !== '未登录') {
            axios.get(`${this.HOST}/projects/${projectId}/`, {
                params: {
                    username: this.username
                }
            }).then(res => {
                if (res.data.data && res.data.data.project && Array.isArray(res.data.data.project.documents)) {
                    // 只保留文档名，或可根据需要保留更多字段
                    this.uploadedFiles = res.data.data.project.documents.map(doc => ({
                        name: doc.title || doc.filename || '',
                        id:doc.id
                    }));
                }
            }).catch(err => {
                this.$message.error('获取文档列表失败: ' + (err.response?.data?.error || err.message));
            });
        }

        let currentSummary = localStorage.getItem('currentSummary')?JSON.parse(localStorage.getItem('currentSummary')):null;
        if(currentSummary!=null&&currentSummary.projectId==this.currentPrjId){
            this.summarizeMsg = currentSummary.summarizeMsg;
            this.$message.info('已恢复上次的总结内容')
        }  
    },
    mounted() {
        this.startLineAnimation(this.summarizeMsg)
    },
    computed: {
        animatedHtml() {
            let arr = this.displayLines.slice();
            if (this.currentLine) {
                arr.push(this.currentLine + '<span class="typing-cursor">|</span>');
            }
            return this.markdownToHtml(arr.join('\n'));
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
                    highlight: (code) => {
                        return hljs.highlightAuto(code).value
                    }
                })
            );
            return marked.parse(message);
        },

        gotoChat() {
            this.$router.push({ path: '/chat' });
        },
        gotoTest() {
            this.$router.push({ path: '/test' });
        },
        output(){
            // 1. 检查内容是否为空
            if (!this.summarizeMsg || this.summarizeMsg.trim() === '') {
                this.$message.warning('暂无可导出的内容');
                return;
            }
            // 2. 获取要导出的内容（markdown格式）
            const content = this.summarizeMsg;
            // 3. 创建Blob对象，类型为markdown
            const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
            // 4. 创建下载链接
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = '用户'+this.username+'_文档总结.md'; // 导出为markdown文件
            // 5. 触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            // 6. 释放URL对象
            window.URL.revokeObjectURL(url);
        },
        gotoPrj(){
            this.$router.push({ path: '/project' });
        },

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
            console.log(response.data)
            this.$message.success(`${file.name} 上传成功`);
            // 新增：添加到已上传文件列表
            this.uploadedFiles.push({ name: file.name });
        },

        // 处理文件行选择
        handleFileRowSelect(row) {
            this.selectedFileRow = row;
            this.selectedFileName = row ? row.name : '';
        },

        onFileRadioChange(row) {
            this.selectedFileRow = row;
            this.selectedFileName = row.name;
        },

        startLineAnimation(msg) {
            if (this.typingTimer) {
                clearTimeout(this.typingTimer);
                this.typingTimer = null;
            }
            this.displayLines = [];
            this.currentLine = '';
            this.lineIdx = 0;
            this.typingLines = msg.split(/\r?\n/);
            this.typeNextChar();
        },
        typeNextChar() {
            if (this.lineIdx >= this.typingLines.length) {
                this.currentLine = '';
                this.displayLines = this.typingLines.slice();
                return;
            }
            const line = this.typingLines[this.lineIdx];
            if (this.currentLine.length < line.length) {
                this.currentLine += line[this.currentLine.length];
                this.typingTimer = setTimeout(this.typeNextChar, 10);
            } else {
                this.displayLines.push(this.currentLine);
                this.currentLine = '';
                this.lineIdx++;
                this.typingTimer = setTimeout(this.typeNextChar, 1);
            }
        },
        generateSummary(){
            this.loading = true;
            const fileId = this.selectedFileId;
            setTimeout(() => {
                axios.get(this.url, {
                    params: {
                        fileId: fileId
                    }
                }).then((response) => {
                    this.summarizeMsg = response.data.AIMessage;
                    this.loading = false;
                    this.startLineAnimation(this.summarizeMsg);
                    localStorage.setItem('currentSummary', JSON.stringify({'summarizeMsg':this.summarizeMsg || '','projectId':this.currentPrjId || ''}));
                })
                .catch(error => {
                    this.loading = false;
                    this.$message.error('获取AI回复失败:' + error.message);
                });
            }, 5000);
        },
    }
};
</script>