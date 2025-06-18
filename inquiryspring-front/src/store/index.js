import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    selectedPrjId:0,
    selectedPrjName:'',
    chatHistory: [], // 全局对话历史
    user: {
      username: '',
      isLoggedIn: false
    }
  },
  getters: {
    getSelectedPrjId:state=>state.selectedPrjId,
    getSelectedPrjName:state=>state.selectedPrjName,
    getChatHistory: state => state.chatHistory,
    getUserInfo: state => state.user,
    getUsername: state => state.user.username,
    isLoggedIn: state => state.user.isLoggedIn
  },
  mutations: {
    setSelectedPrjId(state,id){
      state.selectedPrjId = id;
    },
    setSelectedPrjName(state,name){
      state.selectedPrjName = name;
    },
    setChatHistory(state, history) {
      state.chatHistory = history;
    },
    addChatMessage(state, message) {
      state.chatHistory.push(message);
    },
    clearChatHistory(state) {
      state.chatHistory = [];
    },
    setUserInfo(state, userInfo) {
      state.user.username = userInfo.username;
      state.user.isLoggedIn = true;
    },
    clearUserInfo(state) {
      state.user.username = '';
      state.user.isLoggedIn = false;
    },
    SET_CURRENT_PROJECT(state, project) {
      state.selectedPrjId = project.id;
      state.selectedPrjName = project.name;
    }
  },
  actions: {
    updateSelectedPrjId({commit},id){
      commit('setSelectedPrjId',id);
    },
    updateSelectedPrjName({commit},name){
      commit('setSelectedPrjName',name);
    },
    updateChatHistory({commit}, history) {
      commit('setChatHistory', history);
    },
    addChatMessage({commit}, message) {
      commit('addChatMessage', message);
    },
    clearChatHistory({commit}) {
      commit('clearChatHistory');
    },
    updateUserInfo({commit}, userInfo) {
      commit('setUserInfo', userInfo);
    },
    logout({commit}) {
      commit('clearUserInfo');
    },
    setCurrentProject({commit}, project) {
      commit('SET_CURRENT_PROJECT', project);
    },
    loginSuccess({commit}, userInfo) {
      commit('setUserInfo', userInfo);
    },
    restoreUserInfo({commit}, userInfo) {
      commit('setUserInfo', userInfo);
    }
  },
  modules: {
  }
})
