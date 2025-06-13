import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
  state: {
    selectedPrjId:0,
    selectedPrjName:'',
    chatHistory: [] // 新增：全局对话历史
  },
  getters: {
    getSelectedPrjId:state=>state.selectedPrjId,
    getSelectedPrjName:state=>state.selectedPrjName,
    getChatHistory: state => state.chatHistory // 新增getter
  },
  mutations: {
    setSelectedPrjId(state,id){
      state.selectedPrjId = id;
    },
    setSelectedPrjName(state,name){
      state.selectedPrjName = name;
    },
    setChatHistory(state, history) { // 新增mutation
      state.chatHistory = history;
    },
    addChatMessage(state, message) { // 新增mutation
      state.chatHistory.push(message);
    },
    clearChatHistory(state) { // 新增mutation
      state.chatHistory = [];
    }
  },
  actions: {
    updateSelectedPrjId({commit},id){
      commit('setSelectedPrjId',id);
    },
    updateSelectedPrjName({commit},name){
      commit('setSelectedPrjName',name);
    },
    updateChatHistory({commit}, history) { // 新增action
      commit('setChatHistory', history);
    },
    addChatMessage({commit}, message) { // 新增action
      commit('addChatMessage', message);
    },
    clearChatHistory({commit}) { // 新增action
      commit('clearChatHistory');
    }
  },
  modules: {
  }
})
