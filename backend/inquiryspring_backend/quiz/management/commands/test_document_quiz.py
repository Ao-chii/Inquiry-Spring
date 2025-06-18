"""
测试文档上传生成测验功能的管理命令
用法: python manage.py test_document_quiz
"""

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from inquiryspring_backend.documents.models import Document
from inquiryspring_backend.ai_services.rag_engine import RAGEngine
from inquiryspring_backend.ai_services import process_document_for_rag
import tempfile
import os


class Command(BaseCommand):
    help = '测试文档上传生成测验功能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file-path',
            type=str,
            help='测试文档的路径',
        )
        parser.add_argument(
            '--question-count',
            type=int,
            default=5,
            help='生成题目数量',
        )
        parser.add_argument(
            '--difficulty',
            type=str,
            default='medium',
            choices=['easy', 'medium', 'hard'],
            help='题目难度',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 开始测试文档上传生成测验功能'))
        
        file_path = options.get('file_path')
        question_count = options['question_count']
        difficulty = options['difficulty']
        
        if file_path and os.path.exists(file_path):
            # 使用指定的文件
            self.test_with_file(file_path, question_count, difficulty)
        else:
            # 创建测试文档
            self.test_with_sample_document(question_count, difficulty)

    def test_with_file(self, file_path, question_count, difficulty):
        """使用指定文件测试"""
        self.stdout.write(f'📄 使用文件: {file_path}')
        
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                filename = os.path.basename(file_path)
                
                # 创建文档记录
                document = Document.objects.create(
                    title=filename,
                    file=SimpleUploadedFile(filename, file_content),
                    file_type=self._get_file_type(filename),
                    file_size=len(file_content),
                    is_processed=False
                )
                
                self.process_and_generate_quiz(document, question_count, difficulty)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 文件处理失败: {e}'))

    def test_with_sample_document(self, question_count, difficulty):
        """使用示例文档测试"""
        self.stdout.write('📄 创建示例文档进行测试')
        
        # 创建示例文档内容
        sample_content = """
        机器学习基础知识

        机器学习是人工智能的一个重要分支，它使计算机能够在没有明确编程的情况下学习和改进。

        主要类型：
        1. 监督学习：使用标记数据训练模型，如分类和回归问题。
        2. 无监督学习：从未标记数据中发现模式，如聚类和降维。
        3. 强化学习：通过与环境交互学习最优策略。

        常用算法：
        - 线性回归：用于预测连续值
        - 决策树：易于理解和解释的分类算法
        - 神经网络：模拟人脑神经元的复杂模型
        - 支持向量机：在高维空间中寻找最优分类边界

        评估指标：
        - 准确率：正确预测的比例
        - 精确率：预测为正例中实际为正例的比例
        - 召回率：实际正例中被正确预测的比例
        - F1分数：精确率和召回率的调和平均数

        机器学习在图像识别、自然语言处理、推荐系统等领域有广泛应用。
        """
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(sample_content)
                temp_path = f.name
            
            # 创建文档记录
            with open(temp_path, 'rb') as f:
                document = Document.objects.create(
                    title='机器学习基础知识.txt',
                    file=SimpleUploadedFile('机器学习基础知识.txt', f.read()),
                    file_type='txt',
                    file_size=len(sample_content.encode('utf-8')),
                    is_processed=False
                )
            
            # 清理临时文件
            os.unlink(temp_path)
            
            self.process_and_generate_quiz(document, question_count, difficulty)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 示例文档创建失败: {e}'))

    def process_and_generate_quiz(self, document, question_count, difficulty):
        """处理文档并生成测验"""
        try:
            self.stdout.write(f'📝 文档创建成功: ID={document.id}, 标题={document.title}')
            
            # 处理文档进行RAG
            self.stdout.write('🔄 开始处理文档进行RAG...')
            rag_success = process_document_for_rag(document.id, force_reprocess=True)
            
            if not rag_success:
                self.stdout.write(self.style.ERROR('❌ 文档RAG处理失败'))
                return
            
            self.stdout.write(self.style.SUCCESS('✅ 文档RAG处理成功'))
            
            # 创建RAG引擎并生成测验
            self.stdout.write('🤖 开始生成测验...')
            rag_engine = RAGEngine(document_id=document.id)
            
            user_query = f"基于文档《{document.title}》生成{question_count}道{difficulty}难度的测验题目"
            
            quiz_result = rag_engine.handle_quiz(
                user_query=user_query,
                document_id=document.id,
                question_count=question_count,
                question_types=['MC', 'TF', 'SA'],
                difficulty=difficulty
            )
            
            if "error" in quiz_result:
                self.stdout.write(self.style.ERROR(f'❌ 测验生成失败: {quiz_result["error"]}'))
                return
            
            # 显示生成的题目
            quiz_data = quiz_result.get("quiz_data", [])
            self.stdout.write(self.style.SUCCESS(f'✅ 测验生成成功！共生成 {len(quiz_data)} 道题目'))
            
            for i, question in enumerate(quiz_data, 1):
                self.stdout.write(f'\n📋 题目 {i}:')
                self.stdout.write(f'   类型: {question.get("type", "未知")}')
                self.stdout.write(f'   内容: {question.get("content", question.get("question", ""))[:100]}...')
                self.stdout.write(f'   难度: {question.get("difficulty", "未知")}')
                
                if question.get("options"):
                    self.stdout.write(f'   选项: {", ".join(question["options"])}')
                
                self.stdout.write(f'   答案: {question.get("correct_answer", "未知")}')
                
                if question.get("explanation"):
                    self.stdout.write(f'   解析: {question["explanation"][:100]}...')
            
            # 显示统计信息
            self.stdout.write(f'\n📊 测验统计:')
            self.stdout.write(f'   文档ID: {document.id}')
            self.stdout.write(f'   文档标题: {document.title}')
            self.stdout.write(f'   题目数量: {len(quiz_data)}')
            self.stdout.write(f'   难度级别: {difficulty}')
            
            # 显示题型分布
            type_count = {}
            for q in quiz_data:
                q_type = q.get("type", "未知")
                type_count[q_type] = type_count.get(q_type, 0) + 1
            
            self.stdout.write(f'   题型分布: {dict(type_count)}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 处理过程失败: {e}'))

    def _get_file_type(self, filename):
        """根据文件名确定文件类型"""
        if filename.lower().endswith('.pdf'):
            return 'pdf'
        elif filename.lower().endswith('.docx'):
            return 'docx'
        elif filename.lower().endswith('.txt'):
            return 'txt'
        elif filename.lower().endswith('.md'):
            return 'md'
        else:
            return 'unknown'
