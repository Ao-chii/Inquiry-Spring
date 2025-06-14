import time
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Runs a suite of tests against the RAGEngine to verify its core functionality.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cleanup',
            action='store_true',
            help='Skip cleaning up test documents after tests',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='Gemini API密钥，如不提供将使用模拟响应',
        )

    def handle(self, *args, **options):
        # 设置API密钥
        api_key = options.get('api_key')
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            self.stdout.write(self.style.SUCCESS(f"已设置Gemini API密钥"))
        else:
            self.stdout.write(self.style.WARNING("未提供API密钥，将使用模拟响应"))
            
        # 延迟导入，避免循环依赖
        from apps.documents.models import Document
        from apps.ai_services.rag_engine import RAGEngine
        
        self.stdout.write(self.style.SUCCESS("🚀 Starting RAGEngine Functionality Test Suite..."))
        self.RAGEngine = RAGEngine  # 存储类引用以便在测试方法中使用

        # 1. Setup: Create a test document
        self.stdout.write("\n" + self.style.HTTP_INFO("STEP 1: Setting up test environment..."))
        try:
            test_doc_content = """Python is a high-level, general-purpose programming language.
Its design philosophy emphasizes code readability with the use of significant indentation.
Python is dynamically-typed and garbage-collected.
A key feature of Python is its support for multiple programming paradigms, including structured, object-oriented and functional programming.
The list is a versatile data structure in Python, capable of holding items of different types."""
            
            test_doc = Document.objects.create(
                title="Python Test Document",
                content=test_doc_content,
                is_processed=False
            )
            self.stdout.write(self.style.SUCCESS(f"  ✅ Created test document (ID: {test_doc.id})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed to create test document: {e}"))
            return

        # 2. Instantiate the RAGEngine
        # We will instantiate it within each test to ensure a clean state
        self.stdout.write(self.style.HTTP_INFO("STEP 2: RAGEngine will be instantiated for each mode."))

        # 3. Run tests for each mode
        self.stdout.write("\n" + self.style.HTTP_INFO("STEP 3: Running tests..."))
        
        # Test Chat Mode
        self._test_chat_mode(test_doc.id)
        
        # Test Quiz Mode
        self._test_quiz_mode(test_doc.id)

        # Test Summary Mode
        self._test_summary_mode(test_doc.id)

        # 4. Cleanup
        if not options['skip_cleanup']:
            self.stdout.write("\n" + self.style.HTTP_INFO("STEP 4: Cleaning up test environment..."))
            try:
                test_doc.delete()
                self.stdout.write(self.style.SUCCESS("  ✅ Deleted test document."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Failed to clean up test document: {e}"))

        self.stdout.write("\n" + self.style.SUCCESS("🎉 Test Suite Finished!"))

    def _test_chat_mode(self, doc_id):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED("\n--- Testing Chat Mode ---"))
        engine_with_doc = self.RAGEngine(document_id=doc_id)
        
        # Process the document first
        self.stdout.write("  - Processing and embedding document...")
        success = engine_with_doc.process_and_embed_document()
        if not success:
            self.stdout.write(self.style.ERROR("    ❌ Document processing failed. Aborting chat test with doc."))
            return
        self.stdout.write(self.style.SUCCESS("    ✅ Document processed successfully."))
        
        # Test 1: Chat WITH document context (RAG)
        query_with_doc = "What is a list in Python?"
        self.stdout.write(f"  - Test 1: Chat WITH document (Query: '{query_with_doc}')")
        response = engine_with_doc.handle_chat(query=query_with_doc, document_id=doc_id)
        if response and not response.get('error'):
            self.stdout.write(self.style.SUCCESS(f"    ✅ Got Answer: '{response['answer'][:50]}...'"))
            self.stdout.write(self.style.SUCCESS(f"    ✅ Sources found: {len(response['sources'])}"))
            assert len(response['sources']) > 0, "Should have found sources"
        else:
            self.stdout.write(self.style.ERROR(f"    ❌ Test Failed. Response: {response}"))

        # Test 2: Chat WITHOUT document context
        engine_without_doc = self.RAGEngine()
        query_without_doc = "What is the capital of France?"
        self.stdout.write(f"\n  - Test 2: Chat WITHOUT document (Query: '{query_without_doc}')")
        response = engine_without_doc.handle_chat(query=query_without_doc)
        if response and not response.get('error'):
            self.stdout.write(self.style.SUCCESS(f"    ✅ Got Answer: '{response['answer'][:50]}...'"))
            self.stdout.write(self.style.SUCCESS(f"    ✅ Sources found: {len(response['sources'])}"))
            assert len(response['sources']) == 0, "Should have no sources"
        else:
            self.stdout.write(self.style.ERROR(f"    ❌ Test Failed. Response: {response}"))

    def _test_quiz_mode(self, doc_id):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED("\n--- Testing Quiz Mode ---"))
        
        # Test 1: Quiz WITH document context
        engine_with_doc = self.RAGEngine(document_id=doc_id)
        query_with_doc = "Give me 2 easy multiple choice questions about Python lists"
        self.stdout.write(f"  - Test 1: Quiz WITH document (Query: '{query_with_doc}')")
        response = engine_with_doc.handle_quiz(user_query=query_with_doc, document_id=doc_id)
        if response and not response.get('error') and response.get('quiz_id'):
            self.stdout.write(self.style.SUCCESS(f"    ✅ Quiz created successfully (ID: {response['quiz_id']})"))
            self.stdout.write(self.style.SUCCESS(f"    ✅ Generated {len(response['quiz_data'])} questions."))
        else:
            self.stdout.write(self.style.ERROR(f"    ❌ Test Failed. Response: {response}"))

        # Test 2: Quiz WITHOUT document context
        engine_without_doc = self.RAGEngine()
        query_without_doc = "Generate a hard question about quantum physics"
        self.stdout.write(f"\n  - Test 2: Quiz WITHOUT document (Query: '{query_without_doc}')")
        response = engine_without_doc.handle_quiz(user_query=query_without_doc)
        if response and not response.get('error') and response.get('quiz_id'):
            self.stdout.write(self.style.SUCCESS(f"    ✅ Quiz created successfully (ID: {response['quiz_id']})"))
            self.stdout.write(self.style.SUCCESS(f"    ✅ Generated {len(response['quiz_data'])} questions."))
        else:
            self.stdout.write(self.style.ERROR(f"    ❌ Test Failed. Response: {response}"))

    def _test_summary_mode(self, doc_id):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED("\n--- Testing Summary Mode ---"))
        
        # Test 1: Summary WITH document (correct usage)
        engine_with_doc = self.RAGEngine(document_id=doc_id)
        self.stdout.write(f"  - Test 1: Summary WITH document (ID: {doc_id})")
        response = engine_with_doc.handle_summary(document_id=doc_id)
        if response and not response.get('error'):
            self.stdout.write(self.style.SUCCESS(f"    ✅ Summary generated: '{response.get('text', '')[:50]}...'"))
        else:
            self.stdout.write(self.style.ERROR(f"    ❌ Test Failed. Response: {response}"))

        # Test 2: Summary WITHOUT document (incorrect usage)
        engine_without_doc = self.RAGEngine()
        self.stdout.write(f"\n  - Test 2: Summary WITHOUT document (expecting error)")
        response = engine_without_doc.handle_summary(document_id=None)
        if response and response.get('error'):
            self.stdout.write(self.style.SUCCESS(f"    ✅ Correctly received error: '{response['error']}'"))
        else:
            self.stdout.write(self.style.ERROR(f"    ❌ Test Failed. Expected an error but got: {response}")) 