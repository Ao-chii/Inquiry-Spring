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
            <el-menu-item @click="gotoChat" index="2" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px)">
                <i class="el-icon-chat-dot-round"></i>
                <span>智能答疑</span>
            </el-menu-item>
            <el-menu-item @click="gotoSummarize" index="3" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px)">
                <i class="el-icon-chat-dot-round"></i>
                <span>智慧总结</span>
            </el-menu-item>
            <el-menu-item index="1" style="border-radius: 8px; margin: 0 8px; width: calc(100% - 16px); background: linear-gradient(135deg, #5a4a3a 0%, #3a2e24 100%); color: white; box-shadow: 0 2px 8px rgba(90, 74, 58, 0.3)">
                <i class="el-icon-edit" style="color: white"></i>
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
        <el-main style="padding: 20px; display: flex; flex-direction: column; height: 100%; background-color: rgba(255,255,255,0.7); border-radius: 16px; margin: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid rgba(139, 115, 85, 0.1)">
            <!-- <div class="content-container" style="flex: 1; display: flex; flex-direction: column; gap: 30px;"> -->
                <el-col style="width: 100%; padding: 30px; background: rgba(255,255,255,0.9); border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: flex; gap: 48px; align-items: flex-start; margin-bottom: 15px;">
                    <div style="flex: 1; padding: 10px;">
                        <h3 style="margin-bottom: 15px; display: flex; align-items: center; gap: 5px;">
                            选择文件
                            <el-tooltip content="选择您上传的材料或学习笔记，生成测试题目" placement="right">
                                <i class="el-icon-question" style="color: #8b7355; font-size: 16px;"></i>
                            </el-tooltip>
                        </h3>
                        <!-- <el-upload
                        class="upload-demo"
                        drag
                        action="/api/test/"
                        multiple>
                        <i class="el-icon-upload" style="color: #8b7355;"></i>
                        <div class="el-upload__text" style="color: #5a4a3a;">将文件拖到此处，或<em style="color: #8b7355;">点击上传</em></div>
                        <div class="el-upload__tip" slot="tip" style="color: #8b7355;">支持word,pdf格式</div>
                        </el-upload> -->

                        <!-- 新增：已上传文件表格，单独分区 -->
                        <div v-if="uploadedFiles.length" style="margin: 50px 0 0 0; padding: 16px 12px; background: #f8f6f2; border-radius: 8px; box-shadow: 0 2px 8px rgba(139,115,85,0.06); border: 1px solid #e8dfc8; width: 70%; max-width: 400px; min-width: 220px; box-sizing: border-box; display: flex; flex-direction: column; align-items: center;">
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
                    </div>
                    <div style="flex: 1; padding: 15px;">
                        <h3 style="margin-bottom: 15px; display: flex; align-items: center; gap: 5px;">
                            测试设置
                            <el-tooltip content="个性化生成你所需要的测试题目" placement="right">
                                <i class="el-icon-question" style="color: #8b7355; font-size: 16px;"></i>
                            </el-tooltip>
                        </h3>
                        <el-form ref="testReq" :model="testReq" label-width="80px">
                            <el-form-item label="题目数量">
                                 <div class="block">
                                    <el-slider
                                    v-model="testReq.num"
                                    show-input>
                                    </el-slider>
                                </div>
                            </el-form-item>
                            <el-form-item label="题目类型">
                                <el-checkbox-group v-model="testReq.type">
                                <el-checkbox label="单选题" name="type"></el-checkbox>
                                <el-checkbox label="多选题" name="type"></el-checkbox>
                                <el-checkbox label="判断题" name="type"></el-checkbox>
                                <el-checkbox label="填空题" name="type"></el-checkbox>
                                <el-checkbox label="简答题" name="type"></el-checkbox>
                                </el-checkbox-group>
                            </el-form-item>
                            <el-form-item label="题目难度">
                                <el-radio-group v-model="testReq.level">
                                <el-radio label="简单"></el-radio>
                                <el-radio label="中等"></el-radio>
                                <el-radio label="困难"></el-radio>
                                </el-radio-group>
                            </el-form-item>
                            <el-form-item label="其他要求">
                                <el-input type="textarea" v-model="testReq.desc"></el-input>
                            </el-form-item>
                            <el-form-item>
                                <v-btn @click="generateTest" color="#8b7355" style="color: white;">
                                    立即生成
                                </v-btn>
                            </el-form-item>
                        </el-form>
                    </div>
                </el-col>
                <el-col v-show="testVisible" style="padding: 20px; background: rgba(255,255,255,0.9); border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
                    <div v-if="loading" style="display:flex;align-items:center;justify-content:center;height:300px;">
                        <!-- 三点跳动加载动画 -->
                        <div class="loading-dots">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                    <div v-else>
                        <!-- 题目内容区域，原有内容整体包裹到这里 -->
                        <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 20px;">
                        </div>
                        <v-expansion-panels
                        v-model="panel"
                        multiple
                        >
                        <v-expansion-panel
                            v-for="(item,i) in items"
                            :key="i"
                            style="margin-bottom: 10px; border: 1px solid rgba(139, 115, 85, 0.1); will-change: height;"
                        >
                            <v-expansion-panel-header 
                                expand-icon="mdi-menu-down" 
                                style="color: #5a4a3a; font-weight: 500;"
                                :class="{'v-expansion-panel-header--active': panel.includes(i)}"
                            >
                                题目 {{ item }}
                            </v-expansion-panel-header>
                            <v-expansion-panel-content 
                                style="color: #5a4a3a; line-height: 1.6; padding: 15px;"
                                v-if="panel.includes(i)"
                            >
                            <el-row>
                                <div style="flex:1;">
                                    <div v-html="markMessage(question[i]?.type ? ('**' + question[i].type + '**') : '')"></div>
                                    <div v-html="markMessage(question[i]?.question)"></div>
                                </div>
                            </el-row>
                            <el-row>
                                <!-- 单选题 - 四个小圆圈 -->
                                <div v-if="question[i]?.type==='单选题'" style="margin-top: 15px;">
                                    <div v-for="(option, optIndex) in question[i]?.options || []"
                                         :key="optIndex"
                                         class="option-item"
                                         style="display: flex; align-items: center; margin-bottom: 10px; cursor: pointer;"
                                         @click="selectSingleOption(i, getOptionId(option, optIndex))">
                                        <div class="radio-circle"
                                             :class="{ 'selected': answer[i] === getOptionId(option, optIndex) }"
                                             style="width: 20px; height: 20px; border: 2px solid #8b7355; border-radius: 50%; margin-right: 10px; display: flex; align-items: center; justify-content: center;">
                                            <div v-if="answer[i] === getOptionId(option, optIndex)"
                                                 style="width: 10px; height: 10px; background: #8b7355; border-radius: 50%;"></div>
                                        </div>
                                        <span style="color: #5a4a3a;">{{ getOptionText(option) }}</span>
                                    </div>
                                </div>

                                <!-- 多选题 - 四个小圆圈，可多选 -->
                                <div v-else-if="question[i]?.type==='多选题'" style="margin-top: 15px;">
                                    <div v-for="(option, optIndex) in question[i]?.options || []"
                                         :key="optIndex"
                                         class="option-item"
                                         style="display: flex; align-items: center; margin-bottom: 10px; cursor: pointer;"
                                         @click="toggleMultipleOption(i, getOptionId(option, optIndex))">
                                        <div class="checkbox-circle"
                                             :class="{ 'selected': isMultipleSelected(i, getOptionId(option, optIndex)) }"
                                             style="width: 20px; height: 20px; border: 2px solid #8b7355; border-radius: 50%; margin-right: 10px; display: flex; align-items: center; justify-content: center;">
                                            <div v-if="isMultipleSelected(i, getOptionId(option, optIndex))"
                                                 style="width: 10px; height: 10px; background: #8b7355; border-radius: 50%;"></div>
                                        </div>
                                        <span style="color: #5a4a3a;">{{ getOptionText(option) }}</span>
                                    </div>
                                </div>

                                <!-- 判断题 - 两个小圆圈 -->
                                <div v-else-if="question[i]?.type==='判断题'" style="margin-top: 15px;">
                                    <div v-for="(option, optIndex) in (question[i]?.options || [{text: '正确', id: 'A'}, {text: '错误', id: 'B'}])"
                                         :key="optIndex"
                                         class="option-item"
                                         style="display: flex; align-items: center; margin-bottom: 10px; cursor: pointer;"
                                         @click="selectSingleOption(i, getOptionId(option, optIndex))">
                                        <div class="radio-circle"
                                             :class="{ 'selected': answer[i] === getOptionId(option, optIndex) }"
                                             style="width: 20px; height: 20px; border: 2px solid #8b7355; border-radius: 50%; margin-right: 10px; display: flex; align-items: center; justify-content: center;">
                                            <div v-if="answer[i] === getOptionId(option, optIndex)"
                                                 style="width: 10px; height: 10px; background: #8b7355; border-radius: 50%;"></div>
                                        </div>
                                        <span style="color: #5a4a3a;">{{ getOptionText(option) }}</span>
                                    </div>
                                </div>

                                <!-- 填空题 -->
                                <div v-else-if="question[i]?.type==='填空题'" style="margin-top: 15px;">
                                    <el-input
                                        v-model="answer[i]"
                                        placeholder="请输入答案"
                                        style="width: 100%;">
                                    </el-input>
                                </div>

                                <!-- 简答题 -->
                                <div v-else-if="question[i]?.type==='简答题'" style="margin-top: 15px;">
                                    <el-input
                                        v-model="answer[i]"
                                        type="textarea"
                                        :rows="4"
                                        placeholder="请输入答案"
                                        style="width: 100%;">
                                    </el-input>
                                </div>

                                <span v-if="answerStatus && answerStatus[i] === true" style="color:#4caf50;margin-left:10px;">✔ 正确</span>
                                <span v-else-if="answerStatus && answerStatus[i] === false" style="color:#f44336;margin-left:10px;">✘ 错误，正确答案：{{ question[i].answer }}</span>
                            </el-row>
                            <el-row v-if="showAnalysis && showAnalysis[i]">
                                <div style="margin-top: 10px; color: #8b7355;">
                                    <strong>解析:</strong>
                                    <div v-html="markMessage(question[i].explanation || question[i].analysis)"></div>
                                </div>
                            </el-row>
                            </v-expansion-panel-content>
                        </v-expansion-panel>
                        </v-expansion-panels>
                        <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 20px;">
                            <v-btn v-if="panel.length < items" @click="all" color="#8b7355" style="color: white;">
                                全部展开
                            </v-btn>
                            <v-btn v-else @click="none" color="#e8dfc8" style="color: #5a4a3a;">
                                收起
                            </v-btn>
                            <v-btn @click="submitAns" color="#8b7355" style="color: white;">
                                提交答案
                            </v-btn>
                            <v-btn @click="getAnalysis" color="#8b7355" style="color: white;">
                                查看解析
                            </v-btn>
                            <v-btn @click="output" color="#8b7355" style="color: white;">
                                导出
                            </v-btn>
                        </div>
                    </div>
                </el-col>
            <!-- </div> -->
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
        box-shadow: 0 2px 8px rgba(90, 74, 58, 0.3) !important;
        transform: translateY(-1px);
    }
    
    .el-menu-item.is-active i {
        color: white !important;
    }

    .loading-dots {
        display: flex;
        gap: 8px;
    }

    .loading-dots span {
        display: inline-block;
        width: 12px;
        height: 12px;
        background: #8b7355;
        border-radius: 50%;
        animation: bounce 1.2s infinite both;
    }

    .loading-dots span:nth-child(2) {
        animation-delay: 0.2s;
    }

    .loading-dots span:nth-child(3) {
        animation-delay: 0.4s;
    }

    @keyframes bounce {
        0%, 80%, 100% { transform: scale(1); }
        40% { transform: scale(1.5); }
    }

    /* 选项样式 */
    .option-item {
        transition: all 0.2s ease;
    }

    .option-item:hover {
        background-color: rgba(139, 115, 85, 0.05);
        border-radius: 4px;
        padding: 5px;
        margin: -5px;
    }

    .radio-circle, .checkbox-circle {
        transition: all 0.2s ease;
    }

    .radio-circle:hover, .checkbox-circle:hover {
        border-color: #5a4a3a;
        transform: scale(1.1);
    }

    .radio-circle.selected, .checkbox-circle.selected {
        border-color: #8b7355;
        box-shadow: 0 0 0 2px rgba(139, 115, 85, 0.2);
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
            uploadedFiles:[],
            selectedFileRow: null, // 当前选中的文件行对象
            selectedFileName: '', // 当前选中文件名
            selectedFileId: null, // 新增：当前选中的文件id（用于单选）
            panel: [],
            items: 0,
            testVisible:false,
            testReq:{
                num:"",
                type:[],
                level:"",
                desc:""
            },
            q:"ddd",
            options: [],
            question:[],
            answer: [], // 初始化答案数组
            answerStatus: [], // 答案正误状态
            showAnalysis: [], // 控制每题解析显示
            loading: false, // 是否显示加载动画
            username: '',
            userInitial: '',
            currentPrjId:null
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

        //从localStorage恢复当前项目信息，仅同步id和name到store
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
                    this.currentPrjId = currentProject.id;
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

        let currentQuiz=localStorage.getItem('currentQuiz') ? JSON.parse(localStorage.getItem('currentQuiz')) : [];
        if(currentQuiz!=[]&&currentQuiz.projectId==this.currentPrjId){
            this.question=currentQuiz.questions;
            this.$message.info('已恢复上次的测验内容')
        }
        //this.question = localStorage.getItem('currentQuiz') ? JSON.parse(localStorage.getItem('currentQuiz')) : [];
        if (this.question && this.question.length > 0) {
            this.items = this.question.length;
            this.testVisible = true;
        }
    },
    methods: {
        gotoChat() {
            this.$router.push({ path: '/chat' });
        },
        gotoSummarize() {
            this.$router.push({ path: '/summarize' });
        },
        gotoPrj(){
            this.$router.push({ path: '/project' });
        },
        all () {
            this.panel = [...Array(this.items).keys()].map((k, i) => i)
        },
        // Reset the panel
        none () {
            this.panel = []
        },
        generateTest(){
            this.answerStatus = []; // 答案正误状态
            this.showAnalysis = []; // 控制每题解析显示
            this.answer = []; // 初始化答案数组
            this.loading = true; // 开始加载动画
            this.items = this.testReq.num;

            if(this.items > 0){
                this.testVisible = true;
            }

            // 构建请求数据，映射前端类型到后端类型
            const requestData = {
                question_count: this.testReq.num,
                question_types: this.testReq.type, // 直接使用中文类型名
                difficulty: this.mapDifficulty(this.testReq.level),
                topic: this.testReq.desc || '通用知识',
                document_id:  this.selectedFileId || ''
            };

            console.log('发送测验生成请求:', requestData);

            axios.post('/api/test/', requestData)
                .then(res => {
                    console.log('收到测验响应:', res.data);
                    this.question = res.data.AIQuestion;
                    this.showAnalysis = this.question.map(() => false); // 生成新题后重置解析显示

                    // 初始化答案数组
                    this.answer = this.question.map(q => {
                        if (q.type === '多选题') {
                            return []; // 多选题初始化为空数组
                        }
                        return ''; // 其他题型初始化为空字符串
                    });

                    // --- 展开动画 ---
                    this.panel = [];
                    let idx = 0;
                    const total = this.question.length;
                    const expandTimer = setInterval(() => {
                        if(idx < total) {
                            this.panel.push(idx);
                            idx++;
                        } else {
                            clearInterval(expandTimer);
                        }
                    }, 120); // 每120ms展开一个

                    localStorage.setItem('currentQuiz', JSON.stringify({'questions':this.question,'projectId':this.currentPrjId || ''}));
                })
                .catch(error => {
                    console.error('测验生成失败:', error);
                    this.$message.error('测验生成失败，请重试');
                })
                .finally(() => {
                    this.loading = false; // 加载结束，隐藏动画
                });
        },

        mapDifficulty(level) {
            const difficultyMap = {
                '简单': 'easy',
                '中等': 'medium',
                '困难': 'hard'
            };
            return difficultyMap[level] || 'medium';
        },
        submitAns() {
            // 调用后端API进行答案评判
            const requestData = {
                answers: this.answer,
                questions: this.question
            };

            axios.post('/api/test/evaluate/', requestData)
                .then(response => {
                    const results = response.data.results;
                    this.answerStatus = results.map(result => result.is_correct);

                    // 显示总体结果
                    this.$message({
                        message: response.data.message,
                        type: 'success',
                        duration: 3000
                    });
                })
                .catch(error => {
                    console.error('答案提交失败:', error);
                    this.$message.error('答案提交失败，请重试');

                    // 降级到本地评判
                    this.localAnswerEvaluation();
                });
        },

        localAnswerEvaluation() {
            // 本地答案评判（备用方案）
            this.answerStatus = this.question.map((q, i) => {
                const userAnswer = this.answer[i];
                const correctAnswer = q.answer;

                if (q.type === '多选题') {
                    if (Array.isArray(userAnswer) && Array.isArray(correctAnswer)) {
                        const sortedUser = userAnswer.slice().sort();
                        const sortedCorrect = correctAnswer.slice().sort();
                        return JSON.stringify(sortedUser) === JSON.stringify(sortedCorrect);
                    }
                    return false;
                } else {
                    return String(userAnswer).trim() === String(correctAnswer).trim();
                }
            });
        },
        formatQuestion(q) {
            if (!q) return '';
            return q.replace(/\n/g, '<br>');
        },
        getAnalysis() {
            // 显示所有题目的解析
            this.showAnalysis = this.question.map(() => true);
        },
        // 选项处理方法
        getOptionId(option, index) {
            if (typeof option === 'object' && option.id) {
                return option.id;
            }
            if (typeof option === 'string' && option.match(/^[A-Z]\.\s/)) {
                return option.charAt(0);
            }
            return String.fromCharCode(65 + index); // A, B, C, D...
        },

        getOptionText(option) {
            if (typeof option === 'object' && option.text) {
                return option.text;
            }
            if (typeof option === 'string') {
                // 如果是 "A. 选项内容" 格式，提取内容部分
                if (option.match(/^[A-Z]\.\s/)) {
                    return option.substring(3);
                }
                return option;
            }
            return option;
        },

        // 单选题选择
        selectSingleOption(questionIndex, optionId) {
            this.$set(this.answer, questionIndex, optionId);
        },

        // 多选题切换
        toggleMultipleOption(questionIndex, optionId) {
            if (!this.answer[questionIndex]) {
                this.$set(this.answer, questionIndex, []);
            }

            const currentAnswers = this.answer[questionIndex];
            const index = currentAnswers.indexOf(optionId);

            if (index > -1) {
                // 已选中，取消选择
                currentAnswers.splice(index, 1);
            } else {
                // 未选中，添加选择
                currentAnswers.push(optionId);
            }
        },

        // 检查多选题是否已选中
        isMultipleSelected(questionIndex, optionId) {
            const answers = this.answer[questionIndex];
            return Array.isArray(answers) && answers.includes(optionId);
        },

        getOptionValue(option, index) {
            // 保持向后兼容
            return this.getOptionId(option, index);
        },
        markMessage(message) {
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
        // 处理文件行选择
        handleFileRowSelect(row) {
            this.selectedFileRow = row;
            this.selectedFileName = row ? row.name : '';
        },

        onFileRadioChange(row) {
            this.selectedFileRow = row;
            this.selectedFileName = row.name;
        },

        output(){
            // 1. 检查是否有题目
            if (!this.question || !this.question.length) {
                this.$message.warning('暂无可导出的题目内容');
                return;
            }
            // 2. 构建markdown内容
            let md = `# 小测题目与答案\n\n`;
            this.question.forEach((q, idx) => {
                md += `## 题目${idx + 1}：${q.type || ''}\n`;
                md += q.question ? q.question + '\n' : '';
                if (q.options && Array.isArray(q.options) && q.options.length > 0) {
                    q.options.forEach((opt, i) => {
                        // 选项格式化
                        let optText = '';
                        if (typeof opt === 'object') {
                            optText = (opt.id ? opt.id + '. ' : String.fromCharCode(65 + i) + '. ') + (opt.text || '');
                        } else if (typeof opt === 'string') {
                            optText = opt;
                        }
                        md += `- ${optText}\n`;
                    });
                }
                // 答案
                md += `\n**我的答案：** `;
                const ans = this.answer[idx];
                if (Array.isArray(ans)) {
                    md += ans.join(', ');
                } else {
                    md += ans || '（未作答）';
                }
                if (q.answer !== undefined) {
                    md += `\n**标准答案：** `;
                    if (Array.isArray(q.answer)) {
                        md += q.answer.join(', ');
                    } else {
                        md += q.answer;
                    }
                }
                if (q.explanation || q.analysis) {
                    md += `\n**解析：** ${(q.explanation || q.analysis)}`;
                }
                md += '\n\n---\n\n';
            });
            // 3. 创建Blob对象，类型为markdown
            const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
            // 4. 创建下载链接
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = '用户'+this.username+'_小测题目与答案.md';
            // 5. 触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            // 6. 释放URL对象
            window.URL.revokeObjectURL(url);
        }
    }
};
</script>