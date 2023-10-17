from enum import Enum
from submodules.model.enums import DataTypes, EmbeddingPlatform, LabelingTaskType
from .wizard_function_templates import REFERENCE_CHUNKS_SPLIT


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
                "labels": ["Sufficient", "Needs fix"],
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
                "labels": [
                    "Person",
                    "Date",
                    "Time",
                    "Organization",
                    "IP address",
                    "Phone number",
                    "URL",
                    "E-Mail",
                    "Zip code",
                    "Location",
                ],
                "task_type": LabelingTaskType.INFORMATION_EXTRACTION.value,
                "target_attribute": "reference",
                "bricks": {
                    "group": "personal_identifiers",
                    "type": "extractor",
                },
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
                "code": REFERENCE_CHUNKS_SPLIT.replace(
                    "@@target_attribute@@", "reference"
                ),
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
                "outlier_slice": True,
                "bricks": {
                    "group": "reference_quality",
                    "target_task_name": "Reference Quality",
                },
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
                "outlier_slice": True,
                "bricks": {
                    "group": "reference_complexity",
                    "target_task_name": "Reference Complexity",
                },
            },
        ],
    },
    CognitionProjects.QUERY: {
        "labeling_tasks": [
            {
                "name": "Communication Style",
                "labels": [
                    "Action-seeking",
                    "Fact-oriented",
                    "Information-seeking",
                    "Self-revealing",
                ],
                "bricks": {
                    "group": "communication_style",
                    "target_attribute":"query"
                },
            },
            {
                "name": "Question Type",
                "labels": ["Keyword-question", "Interrogative-question", "Statement-question"],
                "bricks": {
                    "group": "question_type",
                    "target_attribute":"query"
                },
            },
            {
                "name": "Question Quality",
                "labels": ["Good", "Bad"],
                "bricks": {
                    "group": "question_quality",
                    "target_attribute":"query"
                },
            },
            {
                "name": "Question Complexity",
                "labels": ["Low", "Medium", "High"],
                "bricks": {
                    "group": "question_complexity",
                    "target_attribute":"query"
                },
            },
        ],
        "attributes": [
            {
                "bricks": {
                    "group": "rephrased_query",
                    "target_attribute":"query"
                    # "type_lookup": {
                    #     # defaults to text
                    #     "euclidean_distance": DataTypes.FLOAT.value,
                    # },
                },
                "run_code": False,
            },
            {
                "name": "search_queries",
                "type": DataTypes.EMBEDDING_LIST.value,
                "code": REFERENCE_CHUNKS_SPLIT.replace("@@target_attribute@@", "query"),
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
                "bricks": {
                    "group": "fact_is_relevant",
                },
            },
        ],
        "attributes": [
            {
                "bricks": {
                    "group": "argumentation_llm",
                    "target_attribute":"query"
                    # "type_lookup": {
                    #     # defaults to text
                    #     "euclidean_distance": DataTypes.FLOAT.value,
                    # },
                },
                "run_code": False,
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
