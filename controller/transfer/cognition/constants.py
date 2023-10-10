from enum import Enum
from submodules.model.enums import DataTypes, EmbeddingPlatform, LabelingTaskType
from .wizard_function_templates import REFERENCE_CHUNKS


class CognitionProjects(Enum):
    REFERENCE = "REFERENCE"
    QUERY = "QUERY"
    RELEVANCE = "RELEVANCE"

    def get_labeling_tasks(self):
        return TASK_INFO[self].get("labeling_tasks")

    def get_attributes(self):
        return TASK_INFO[self].get("attributes")

    def get_embeddings(self):
        return TASK_INFO[self].get("embeddings")


TASK_INFO = {
    CognitionProjects.REFERENCE: {
        "labeling_tasks": [
            {
                "name": "Reference Quality",
                "labels": ["Good", "Needs fix"],
                "bricks": {
                    "group": "reference_quality",
                    # "function_prefix": "RQ_",
                },
            },
            {
                "name": "Reference Complexity",
                "labels": ["Low", "Medium", "High"],
                "bricks": {
                    "group": "reference_complexity",
                },
            },
            {
                "name": "Reference Type",
                "labels": ["Unknown"],
                # "bricks": {
                #     "group": "reference_type",
                # },
            },
            {
                "name": "Personal Identifiable Information (PII)",
                "labels": ["Person", "Countries", "Date", "Time", "Organization", "IP address", "Phone number", "URL", "E-Mail", "Zip code", "Location"],
                "task_type": LabelingTaskType.INFORMATION_EXTRACTION.value,
                "target_attribute": "reference",
                # "bricks": {
                #     "group": "personal_identifiers",
                #     "type": "extractor",
                # },
            },
        ],
        "attributes": [
            {
                "name": "Language",
                "type": DataTypes.CATEGORY.value,
                "code_build": {"endpoint": "language_detection"},
            },
            {
                "name": "reference_chunks",
                "type": DataTypes.EMBEDDING_LIST.value,
                "code": REFERENCE_CHUNKS.replace("@@target_attribute@@", "reference"),
            },
        ],
        "embeddings": [
            {
                "target": {
                    "attribute": "reference",
                    "platform": "huggingface",
                    "model": {
                        "de": "bert-base-german-cased",
                        "en": "distilbert-base-uncased",
                    },
                },
                "filter": "FROM_WIZARD",
                "outlier_slice": False,
            },
            {
                "target": {
                    "attribute": "reference_chunks",
                    "platform": "huggingface",
                    "model": {
                        "de": "bert-base-german-cased",
                        "en": "distilbert-base-uncased",
                    },
                },
                "filter": "FROM_WIZARD",
                "outlier_slice": False,  # no manual labels yet
            },
        ],
    },
    CognitionProjects.QUERY: {
        "labeling_tasks": [
            {
                "name": "Communication Style",
                "labels": [
                    "action-seeking",
                    "fact-oriented",
                    "information-seeking",
                    "self-revealing",
                ],
                # "bricks": {
                #     "group": "sentiment",
                # },
            },
            {
                "name": "Question Type",
                "labels": ["keyword-query", "interrogative-query", "statement-query"],
                # "bricks": {
                #     "group": "sentiment",
                # },
            },
            {
                "name": "Question Quality",
                "labels": ["Good", "Bad"],
                # "bricks": {
                #     "group": "sentiment",
                # },
            },
        ],
        "attributes": [
            {
                "bricks": {
                    "group": "sentiment",
                    "type_lookup": {
                        # defaults to text
                        "euclidean_distance": DataTypes.FLOAT.value,
                    },
                },
                "run_code": False,
            },
            {
                "name": "search_queries",
                "type": DataTypes.EMBEDDING_LIST.value,
                "code": REFERENCE_CHUNKS.replace("@@target_attribute@@", "query"),
            },
        ],
        "embeddings": [
            {
                "target": {
                    "attribute": "query",
                    "platform": "huggingface",
                    "model": {
                        "de": "bert-base-german-cased",
                        "en": "distilbert-base-uncased",
                    },
                },
                "outlier_slice": False,
            }
        ],
    },
    CognitionProjects.RELEVANCE: {
        "labeling_tasks": [
            {
                "name": "Fact is relevant",
                "labels": [
                    "Yes",
                    "No",
                ],
                # "bricks": {
                #     "group": "sentiment",
                # },
            },
        ],
        "attributes": [
            {
                # "bricks": {
                #     "group": "sentiment",
                #     "type_lookup": {
                #         # defaults to text
                #         "euclidean_distance": DataTypes.FLOAT.value,
                #     },
                # },
                # "run_code": False,
            },
        ],
        "embeddings": [
            {
                "target": {
                    "attribute": "query",
                    "platform": "huggingface",
                    "model": {
                        "de": "bert-base-german-cased",
                        "en": "distilbert-base-uncased",
                    },
                },
                "outlier_slice": False,
            }
        ],
    },
}

DEFAULT_MODEL = {
    EmbeddingPlatform.AZURE.value: None,
    EmbeddingPlatform.COHERE.value: None,
    EmbeddingPlatform.HUGGINGFACE.value: "distilbert-base-uncased",
    EmbeddingPlatform.OPENAI.value: "text-embedding-ada-002",
    EmbeddingPlatform.PYTHON.value: "bag-of-words",
}
