import json

from ingestion.loader import load_documents


def test_document_with_empty_classification_is_rejected(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "a.txt").write_text("hello")

    acl_path = tmp_path / "acl.json"
    acl_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_id": "bad_doc",
                        "title": "Bad Doc",
                        "file_name": "a.txt",
                        "classification": "",
                        "owner_id": "bob_manager",
                        "allowed_roles": ["employee"],
                        "allowed_users": [],
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            }
        )
    )

    corpus = load_documents(str(acl_path), str(docs_dir))
    assert corpus.documents == []
    assert "bad_doc" in corpus.rejected


def test_document_missing_backing_file_is_rejected(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    acl_path = tmp_path / "acl.json"
    acl_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_id": "missing_file_doc",
                        "title": "Missing File",
                        "file_name": "does_not_exist.txt",
                        "classification": "internal",
                        "owner_id": "bob_manager",
                        "allowed_roles": ["employee"],
                        "allowed_users": [],
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            }
        )
    )

    corpus = load_documents(str(acl_path), str(docs_dir))
    assert corpus.documents == []
    assert "missing_file_doc" in corpus.rejected


def test_well_formed_document_with_existing_file_loads(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "good.txt").write_text("hello world")

    acl_path = tmp_path / "acl.json"
    acl_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_id": "good_doc",
                        "title": "Good Doc",
                        "file_name": "good.txt",
                        "classification": "public",
                        "owner_id": "casey_admin",
                        "allowed_roles": ["employee"],
                        "allowed_users": [],
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            }
        )
    )

    corpus = load_documents(str(acl_path), str(docs_dir))
    assert len(corpus.documents) == 1
    assert corpus.rejected == []
