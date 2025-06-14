"""
测试AI服务的脚本
"""
import os
import django
import sys
import google.generativeai as genai

# --- Path setup ---
# To make this script runnable from anywhere, we need to add the backend directory to the Python path.
# This ensures that imports like 'inquiryspring_backend.settings' and 'inquiryspring_backend.ai_services' work correctly.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, 'backend')

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# --- 代理设置 ---
# 你的代理服务器地址和端口
PROXY_HOST = "127.0.0.1"
PROXY_PORT = "7890"
PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"

# 设置HTTP和HTTPS代理环境变量
os.environ['HTTP_PROXY'] = PROXY_URL
os.environ['HTTPS_PROXY'] = PROXY_URL
print(f"已设置代理: HTTP_PROXY={os.environ.get('HTTP_PROXY')}, HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")
# ----------------

# 直接设置API密钥（仅用于测试）
os.environ['GOOGLE_API_KEY'] = "AIzaSyD-Q9HqDZze_LWfHflNV_f1PkqhpET_NJw"  # 替换为你的有效API密钥

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inquiryspring_backend.settings')
django.setup()

# 导入所需模块
from inquiryspring_backend.ai_services.llm_client import LLMClientFactory
from inquiryspring_backend.ai_services.rag_engine import RAGEngine
from inquiryspring_backend.ai_services.models import AIModel


# 测试LLM客户端
def test_llm_client():
    print("=== 测试LLM客户端 ===")
    client = LLMClientFactory.create_client(provider='gemini')
    
    # 简单问答测试
    response = client.generate_text(
        prompt="你好，请介绍一下自己",
        system_prompt="你是InquirySpring系统的AI助手",
        task_type="chat"
    )
    
    print(f"问题: 你好，请介绍一下自己")
    print(f"回答: {response['text']}")
    print(f"tokens使用: {response.get('tokens_used', '未知')}")
    print("\n")

# 测试RAG引擎（如果已有文档）
def test_rag_engine():
    print("=== 测试RAG引擎 ===")
    rag = RAGEngine()
    
    # 如果已有文档，可以尝试查询
    try:
        from backend.inquiryspring_backend.documents.models import Document
        docs = Document.objects.all()
        if not docs.exists():
            # 创建一个测试文档
            print("创建测试文档...")
            test_doc = Document.objects.create(
                title="测试文档",
                content="""这是一个测试文档，用于测试RAG引擎的功能。
                
                机器学习是人工智能的一个子领域，它的核心思想是让计算机系统能够从数据中"学习"，而无需进行明确的编程。
                
                机器学习的主要类型包括：
                1. 监督学习：使用带有"标签"的数据进行训练
                2. 无监督学习：使用没有"标签"的数据进行训练
                3. 强化学习：系统通过与环境的交互来学习
                
                深度学习是机器学习的一个子集，它使用多层人工神经网络来从数据中学习。""",
                is_processed=False
            )
            docs = Document.objects.all()  # 重新获取文档列表
            
        if docs.exists():
            doc = docs.first()
            print(f"使用文档: {doc.title}")
            
            query = "这篇文档的主要内容是什么？为我生成一个关于机器学习的测试问题"
            rag = RAGEngine(document_id=doc.id)  # 初始化RAG引擎时传入document_id
            result = rag.answer_query(query=query)
            
            print(f"问题: {query}")
            print(f"回答: {result.get('text', '未能获取回答')}")  # 使用'text'键而不是'answer'
        else:
            print("数据库中没有可测试的文档")
    except Exception as e:
        print(f"测试RAG引擎时出错: {str(e)}")

def test_gemini_client():
    """测试Gemini客户端"""
    print("=== 测试Gemini客户端 ===")
    
    # 获取API密钥（为了测试，也可以直接设置）
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("警告: 未设置GOOGLE_API_KEY环境变量，请确保数据库中的模型配置有API密钥")
    
    # 创建客户端
    client = LLMClientFactory.create_client(provider='gemini')
    
    # 简单问答测试
    prompt = "你好，请为我简单的介绍一下什么是机器学习。"
    print(f"问题: {prompt}")
    
    try:
        response = client.generate_text(
            prompt=prompt,
            system_prompt="你是InquirySpring系统的智能助手",
            task_type="chat"
        )
        
        print(f"回答: {response['text']}")
        print(f"使用的模型: {response.get('model', '未知')}")
        print(f"tokens使用: {response.get('tokens_used', '未知')}")
        print("测试成功!")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        print("请检查API密钥和网络连接")

def test_specific_gemini_model(model_id_to_test: str):
    """测试指定的Gemini模型ID"""
    print(f"=== 尝试测试 Gemini 模型: {model_id_to_test} ===")
    
    target_model_config = None
    client = None # 初始化 client变量
    try:
        target_model_config = AIModel.objects.get(model_id=model_id_to_test, provider='gemini', is_active=True)
        print(f"数据库中找到模型配置: {target_model_config.name} (ID: {target_model_config.id})")
        client = LLMClientFactory.create_client(model_id=target_model_config.id)
    except AIModel.DoesNotExist:
        print(f"数据库中未找到 model_id='{model_id_to_test}' 的配置。")
        # 根据你 llm_client.py 的改动，它现在会默认尝试 gemini-2.5-flash (应为 gemini-2.5-flash-preview)
        # 我们这里明确指定 provider='gemini' 来让工厂尝试默认的 Gemini 模型
        print(f"将尝试使用 provider='gemini' 的默认配置。")
        client = LLMClientFactory.create_client(provider='gemini') 
        # 打印出实际使用的模型ID，因为它可能与期望的不同
        print(f"LLMClientFactory 创建的客户端实际模型ID为: {client.model_id}")
        if client.model_id != model_id_to_test and model_id_to_test == "gemini-2.5-flash-preview-05-20": # 如果期望的是flash-preview-05-20但拿到别的
             print(f"警告: 期望测试 {model_id_to_test}，但实际可能使用 {client.model_id}。请检查数据库中的默认 Gemini 模型设置或手动添加 '{model_id_to_test}' 的配置。")

    except Exception as e:
        print(f"获取模型 '{model_id_to_test}' 配置或创建客户端时出错: {e}")
        print("将回退尝试使用 provider='gemini' 的默认配置创建客户端")
        try:
            client = LLMClientFactory.create_client(provider='gemini')
            print(f"回退后，LLMClientFactory 创建的客户端实际模型ID为: {client.model_id}")
        except Exception as factory_e:
            print(f"尝试回退创建默认Gemini客户端也失败了: {factory_e}")
            print("测试无法继续。")
            return

    if not client:
        print("错误：未能成功创建 LLM 客户端。测试中止。")
        return

    prompt = f"你好，为我讲解一下什么是卷积神经网络"
    print(f"发送给模型 {client.model_id} 的问题: {prompt}")
    
    try:
        response = client.generate_text(
            prompt=prompt,
            system_prompt=f"你是InquirySpring系统的智能助手。请明确告诉用户你当前是什么模型。",
            task_type="chat"
        )
        
        print(f"来自 {client.model_id} 的回答: {response['text']}")
        print(f"tokens使用: {response.get('tokens_used', '未知')}")
        if "error" in response:
            print(f"模型返回错误: {response['error']}")
            print("测试失败!")
        elif response.get('connection_error'):
            print("测试因网络连接错误而回退到模拟响应。")
        else:
            print("测试成功!")

    except Exception as e:
        print(f"测试模型 {client.model_id} 失败: {str(e)}")
        print("请检查API密钥、网络连接、代理设置以及模型ID是否正确。")

# 运行测试
if __name__ == "__main__":
    api_key_env = os.environ.get('GOOGLE_API_KEY')
    if not api_key_env:
        print("警告: GOOGLE_API_KEY 环境变量未通过脚本顶部设置成功读取!")
    else:
        # 配置genai库使用API密钥，虽然它会自动查找环境变量，但显式配置一下更保险
        # 特别是如果脚本内有修改os.environ的操作
        try:
            genai.configure(api_key=api_key_env)
            print(f"已为 google.generativeai 配置 API 密钥。")
        except Exception as e:
            print(f"配置 google.generativeai API 密钥时出错: {e}")
    
    print("开始AI服务测试...")
    
    # 你在 llm_client.py 中将默认模型改为了 gemini-2.5-flash-preview-tts (但现在数据库默认是 gemini-2.5-flash-preview-05-20)
    # 我们这里也尝试这个，确保你的数据库中有一个 AIModel 记录的 model_id 与此匹配，或者你的 llm_client.py 中的默认逻辑能正确处理
    preferred_model_id = "gemini-2.5-flash-preview-05-20" # 更新为新的目标模型
    # 或者你可以选择一个从 list_available_models() 输出中看到的有效模型
    
    # 检查数据库中是否有这个首选模型
    try:
        db_model_config = AIModel.objects.filter(model_id=preferred_model_id, provider='gemini', is_active=True).first()
        if db_model_config:
            print(f"数据库中找到首选测试模型 '{preferred_model_id}' (数据库ID: {db_model_config.id}) 的配置。")
        else:
            print(f"数据库中未找到模型ID为 '{preferred_model_id}' 的配置。")
            print(f"测试将依赖 LLMClientFactory 使用 provider='gemini' 时的默认模型查找逻辑。")
            # 如果你的 llm_client.py 中的 GeminiClient.__init__ 设置了 gemini-2.5-flash 为硬编码默认，那么即使数据库没有，它也会尝试用这个ID
    except Exception as e:
        print(f"检查首选模型 '{preferred_model_id}' 时出错: {e}")

    test_specific_gemini_model(preferred_model_id)
    #test_gemini_client()
