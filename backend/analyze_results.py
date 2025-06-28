import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
import json

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei'] # 'SimHei' 是一个常用的黑体
matplotlib.rcParams['axes.unicode_minus'] = False # 解决负号显示问题

# --- 配置 ---
RESULTS_FILE_PATH = 'evaluation_results.json'

def analyze_and_visualize():
    """加载结果，计算平均分，并生成可视化图表。"""
    
    with open(RESULTS_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    # --- 计算平均分 ---
    metrics_to_average = [
        'retrieval_relevance_rating',
        'answer_faithfulness_rating',
        'answer_relevance_rating'
    ]
    
    average_scores = df.groupby('mode')[metrics_to_average].mean().reset_index()
    
    print("--- 平均性能得分 (满分5分) ---")
    print(average_scores)
    
    # --- 数据可视化 ---
    # 为了方便绘图，我们将数据从宽格式转换为长格式
    df_long = pd.melt(average_scores, id_vars=['mode'], var_name='metric', value_name='average_rating')
    
    # 定义更美观的标签
    metric_labels = {
        'retrieval_relevance_rating': '检索内容相关性',
        'answer_faithfulness_rating': '答案的基于性',
        'answer_relevance_rating': '答案对问题的相关性'
    }
    df_long['metric'] = df_long['metric'].map(metric_labels)
    
    plt.figure(figsize=(14, 8))
    sns.set_theme(style="whitegrid")
    
    ax = sns.barplot(
        x='metric', 
        y='average_rating', 
        hue='mode', 
        data=df_long,
        palette='viridis' # 使用一个美观的色板
    )
    
    # 在柱状图上显示数值
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.2f}", 
                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                    ha = 'center', va = 'center', 
                    xytext = (0, 9), 
                    textcoords = 'offset points')

    plt.title('不同RAG模式性能对比', fontsize=16)
    plt.xlabel('评估指标', fontsize=12)
    plt.ylabel('平均得分 (1-5分)', fontsize=12)
    plt.ylim(0, 5.5) # 留出顶部空间给数字
    plt.legend(title='RAG模式')
    
    # 保存图表
    plt.savefig('rag_performance_comparison.png', dpi=300)
    print("\n性能对比图已保存为 'rag_performance_comparison.png'")
    
    plt.show()

if __name__ == '__main__':
    analyze_and_visualize() 