"""Paths and namespaces shared by all kgqa modules."""

from pathlib import Path

KGQA_DIR = Path(__file__).resolve().parent
REPO_ROOT = KGQA_DIR.parent

# Original project files (read-only for kgqa).
TBOX_PATH = REPO_ROOT / "output_files" / "tbox.ttl"
ABOX_PATH = REPO_ROOT / "output_files" / "abox.ttl"
QUERIES_DIR = REPO_ROOT / "queries"

# Generated files (git-ignored).
CACHE_DIR = KGQA_DIR / "cache"
CLOSURE_PATH = CACHE_DIR / "closure.nt"
LLM_CACHE_PATH = CACHE_DIR / "llm_responses.jsonl"
LLM_LOG_PATH = KGQA_DIR / "logs" / "llm_calls.jsonl"

# The TBox calls this namespace `ns1:` and the ABox calls it `dbo:`.
# kgqa always uses `sdm:`.
SDM = "http://sdm_upc.org/ontology/"
RES = "http://sdm_upc.org/resource/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"
