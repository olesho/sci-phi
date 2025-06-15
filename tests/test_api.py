import importlib
import sys
import types
from pathlib import Path
import yaml
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def app():
    # Create stub modules required by main
    processor = types.ModuleType("processor")
    from pydantic import BaseModel
    class ProcessInputData(BaseModel):
        uri: str
    def process_pdf(data: ProcessInputData):
        return {"uri": data.uri, "downloaded": True, "is_pdf": True, "file_path": "file.pdf"}
    processor.ProcessInputData = ProcessInputData
    processor.process_pdf = process_pdf
    sys.modules["processor"] = processor

    database = types.ModuleType("database")
    def init_database():
        pass
    def get_all_processed_pdfs():
        return []
    def get_processed_pdf(uri: str):
        return {"uri": uri, "file_path": "file.pdf", "is_downloaded": True, "status": "success", "is_converted": True, "is_extracted": True, "extraction_file_path": "res.json"}
    def get_processed_pdf_by_id(pid: int):
        return {"id": pid, "uri": f"uri{pid}", "is_converted": True, "is_extracted": True, "extraction_file_path": "res.json"}
    def delete_processed_pdf(uri: str):
        return True
    def get_processing_stats():
        return {"total": 0}
    def check_uri_exists(uri: str):
        return None
    def check_content_exists(h: str):
        return None
    def hash_file_content(p: str):
        return "hash"
    def reset_interrupted_conversions():
        return 0
    def reset_interrupted_extractions():
        return 0
    import contextlib
    @contextlib.contextmanager
    def get_db_connection():
        class DummyCursor:
            def execute(self, *args, **kwargs):
                pass
            def fetchall(self):
                return []
            def fetchone(self):
                return (0, 0, 0)
        class DummyConn:
            def cursor(self):
                return DummyCursor()
            def commit(self):
                pass
            def close(self):
                pass
        yield DummyConn()
    database.init_database = init_database
    database.get_all_processed_pdfs = get_all_processed_pdfs
    database.get_processed_pdf = get_processed_pdf
    database.get_processed_pdf_by_id = get_processed_pdf_by_id
    database.delete_processed_pdf = delete_processed_pdf
    database.get_processing_stats = get_processing_stats
    database.check_uri_exists = check_uri_exists
    database.check_content_exists = check_content_exists
    database.hash_file_content = hash_file_content
    database.reset_interrupted_conversions = reset_interrupted_conversions
    database.reset_interrupted_extractions = reset_interrupted_extractions
    database.get_db_connection = get_db_connection
    sys.modules["database"] = database

    conv = types.ModuleType("conversion_service")
    async def convert_pdf_async(uri: str):
        return {"converted": uri}
    async def process_conversion_queue():
        return []
    conv.convert_pdf_async = convert_pdf_async
    conv.process_conversion_queue = process_conversion_queue
    sys.modules["conversion_service"] = conv

    ext = types.ModuleType("extraction_service")
    async def extract_pdf_async(uri: str):
        return {"extracted": uri}
    async def process_extraction_queue():
        return []
    async def extract_pdf_selective_async(uri, fields, models, size):
        return {"extracted": uri, "fields": fields}
    def get_extraction_template():
        return {
            "fields": [{"title": "title"}, {"title": "abstract"}],
            "models": [{"name": "model1"}],
        }
    ext.extract_pdf_async = extract_pdf_async
    ext.process_extraction_queue = process_extraction_queue
    ext.extract_pdf_selective_async = extract_pdf_selective_async
    ext.get_extraction_template = get_extraction_template
    sys.modules["extraction_service"] = ext

    config = types.ModuleType("config")
    def resolve_file_path(p: str):
        return Path(p)
    def get_pdf_conversion_folder(filename: str):
        return Path(filename).parent
    config.resolve_file_path = resolve_file_path
    config.get_pdf_conversion_folder = get_pdf_conversion_folder
    sys.modules["config"] = config

    llm_pkg = types.ModuleType("llm")
    questions_mod = types.ModuleType("llm.questions")
    questions_mod.question_list = []
    llm_mod = types.ModuleType("llm.llm")
    llm_mod.model_list = []
    sys.modules["llm"] = llm_pkg
    sys.modules["llm.questions"] = questions_mod
    sys.modules["llm.llm"] = llm_mod

    sys.path.insert(0, "fastapi_app")
    main = importlib.import_module("main")
    return main.app


def load_spec():
    with open(Path("docs/openapi.yaml"), "r") as f:
        return yaml.safe_load(f)


def test_openapi_valid():
    """Check that the OpenAPI specification loads and exposes basic endpoints."""
    spec = load_spec()
    assert "paths" in spec
    assert "/health" in spec["paths"]


def test_endpoints_from_spec(app):
    """Ensure each endpoint defined in the spec responds without server errors."""
    client = TestClient(app)
    spec = load_spec()
    for path, operations in spec["paths"].items():
        for method in operations.keys():
            url = path.replace("{uri}", "test").replace("{paper_id}", "1")
            if method == "get":
                response = client.get(url)
            elif method == "post":
                body = {}
                if "requestBody" in operations[method]:
                    if path.startswith("/pdfs") and method == "post":
                        body = {"uri": "http://example.com/sample.pdf"}
                    elif path.endswith("/selective"):
                        body = {"selected_fields": ["title"]}
                response = client.post(url, json=body)
            elif method == "delete":
                response = client.delete(url)
            else:
                continue
            assert response.status_code < 500


def test_selective_extraction(app):
    """Verify that the selective extraction endpoint returns the expected data."""
    client = TestClient(app)
    payload = {
        "selected_fields": ["title", "abstract"],
        "selected_models": ["model1"],
        "selected_size": "medium",
    }
    response = client.post("/extract/1/selective", json=payload)
    assert response.status_code == 200
    assert response.json() == {"extracted": "uri1", "fields": ["title", "abstract"]}
