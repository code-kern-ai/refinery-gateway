from submodules.model.enums import EmbeddingPlatform

TERMS_INFO = {
    EmbeddingPlatform.HUGGINGFACE.value: {
        "platform": EmbeddingPlatform.HUGGINGFACE.value,
        "terms": None,
        "link": None,
    },
    EmbeddingPlatform.OPENAI.value: {
        "platform": EmbeddingPlatform.OPENAI.value,
        "terms": "Please note that by enabling this third-party API, you are stating that you accept its addition as a sub-processor under the terms of our Data Processing Agreement. Please be aware that the OpenAI API policies may conflict with your internal data and privacy policies. For more information please check: @@PLACEHOLDER@@. For questions you can contact us at security@kern.ai.",
        "link": "https://openai.com/policies/api-data-usage-policies",
    },
    EmbeddingPlatform.COHERE.value:{
        "platform": EmbeddingPlatform.COHERE.value,
        "terms": "Please note that by enabling this third-party API, you are stating that you accept its addition as a sub-processor under the terms of our Data Processing Agreement. Please be aware that the Cohere API policies may conflict with your internal data and privacy policies. For more information please check: @@PLACEHOLDER@@. For questions you can contact us at security@kern.ai.",
        "link": "https://cohere.com/terms-of-use",
    },
    EmbeddingPlatform.PYTHON.value: {
        "platform": EmbeddingPlatform.PYTHON.value,
        "terms": None,
        "link": None,
    },
    EmbeddingPlatform.AZURE.value: {
        "platform": EmbeddingPlatform.AZURE.value,
        "terms": "Please note that by enabling this third-party API, you are stating that you accept its addition as a sub-processor under the terms of our Data Processing Agreement. Please be aware that the Azure API policies may conflict with your internal data and privacy policies. For more information please check: @@PLACEHOLDER@@. For questions you can contact us at security@kern.ai.",
        "link": "https://www.microsoft.com/en-us/legal/terms-of-use",
    },
}
