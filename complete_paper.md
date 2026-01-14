# An End-to-End AI Clinical Decision Support System Using Retrieval-Augmented Generation

## Abstract

Large Language Models (LLMs) have demonstrated significant potential for enhancing Clinical Decision Support Systems (CDSS) through natural language understanding and generation capabilities. However, their deployment in healthcare settings faces critical challenges, including the generation of factually incorrect information (hallucinations) and limited access to current medical knowledge. Retrieval-Augmented Generation (RAG) addresses these limitations by grounding LLM outputs in external, verifiable knowledge sources. While RAG has shown promise in healthcare applications, existing research predominantly focuses on algorithmic improvements or isolated prototypes, leaving a gap in comprehensive, deployment-ready system architectures. This paper presents the design, implementation, and evaluation of a complete, end-to-end AI-powered CDSS that integrates a modular microservices architecture with a RAG pipeline. The system comprises a React-based frontend for clinician interaction, a FastAPI backend service, and a Qdrant vector database for semantic retrieval of medical guidelines. We detail the architectural components, including a specialized data ingestion pipeline capable of processing complex medical documents, query rewriting mechanisms for conversational context, and adaptive response generation policies. System-level evaluation demonstrates that the proposed architecture achieves sub-second retrieval latency and generates grounded, relevant clinical responses with verifiable source citations. The system mitigates hallucination risks through similarity-based filtering and explicit source attribution. This work contributes a practical, deployment-ready architectural blueprint for modernizing clinical workflows with reliable AI assistance, emphasizing modularity, scalability, and ethical considerations.

**Keywords**: Clinical Decision Support Systems, Retrieval-Augmented Generation, Healthcare AI, Medical Information Retrieval, Vector Databases, Microservices Architecture

## 1. Introduction

Clinical Decision Support Systems (CDSS) have evolved from rule-based expert systems to sophisticated platforms that assist healthcare professionals in making evidence-based decisions at the point of care [1]. The integration of artificial intelligence, particularly Large Language Models (LLMs), has introduced new capabilities for natural language understanding, information synthesis, and contextual reasoning in clinical settings [2]. However, the direct application of LLMs in healthcare encounters fundamental limitations that impede their safe and effective deployment.

The primary challenges include the phenomenon of "hallucinations"—instances where models generate plausible but factually incorrect information [3]. This risk is particularly acute in healthcare, where accuracy is paramount. Additionally, LLMs are constrained by their training data, which may be outdated or lack domain-specific medical knowledge. The static nature of model parameters further limits their ability to incorporate the latest clinical guidelines, research findings, or institution-specific protocols [4].

Retrieval-Augmented Generation (RAG) has emerged as a promising paradigm to address these limitations. RAG enhances LLMs by retrieving relevant documents from external knowledge bases before generating responses, thereby grounding outputs in verifiable evidence [5]. This approach combines the parametric knowledge encoded in LLM weights with non-parametric knowledge stored in external databases, enabling dynamic access to current information without model retraining [6].

Recent surveys have highlighted the theoretical benefits of RAG in healthcare applications [7, 8]. However, a significant gap exists between algorithmic research and practical, deployment-ready systems. Many existing studies focus on component-level analysis, isolated prototypes, or task-specific implementations [9, 10]. These approaches often lack comprehensive architectural blueprints that address real-world constraints such as latency requirements, scalability, integration with clinical workflows, and ethical considerations.

This paper presents an end-to-end, modular AI CDSS framework designed to bridge this gap. Our system leverages a microservices architecture, utilizing a high-performance vector database (Qdrant) for semantic retrieval, a robust backend service (FastAPI), and a clinician-centric frontend (React). Unlike generic RAG implementations, our approach integrates specialized components for processing complex medical documents, managing conversational context, and ensuring response quality through adaptive policies.

The contributions of this work are as follows:

1. **End-to-End Architecture**: We propose a complete, scalable architecture for a RAG-based CDSS, detailing the integration of frontend, backend, and vector database components with clear separation of concerns.

2. **Practical Implementation**: We provide a reference implementation using open-source technologies, demonstrating domain adaptation from general-purpose RAG to a specialized medical CDSS with patient context awareness.

3. **Context-Aware Retrieval**: We demonstrate a pipeline for ingesting and retrieving from authoritative medical guidelines, incorporating query rewriting for conversational context and similarity-based filtering to mitigate hallucinations.

4. **System-Level Evaluation**: We present evaluation results demonstrating the system's performance in terms of retrieval latency, response relevance, and source attribution, providing insights for practical deployment.

The remainder of this paper is organized as follows: Section 2 reviews related work in medical LLMs and RAG systems. Section 3 details the system architecture and component design. Section 4 describes the methodology and implementation details. Section 5 presents the experimental setup and evaluation results. Section 6 discusses limitations and ethical considerations. Section 7 concludes the paper and outlines future research directions.

## 2. Related Work

### 2.1 Large Language Models in Healthcare

The application of LLMs in healthcare has gained significant attention following the success of general-purpose models such as GPT-4 [11] and LLaMA [12]. Domain-specific models including BioBERT [13] and ClinicalBERT [14] have been developed through fine-tuning on biomedical corpora, demonstrating improved performance on medical language understanding tasks. However, these models still face challenges with contextual data, knowledge updates, and the risk of generating inaccurate information [15].

Med-PaLM [15] represents a notable effort to adapt LLMs for clinical tasks, showing promising results in clinical knowledge retrieval and decision-making. However, evaluations revealed limitations including bias and the generation of potentially harmful responses, highlighting the need for additional safeguards and grounding mechanisms.

### 2.2 Retrieval-Augmented Generation

RAG was originally introduced by Lewis et al. [5] as a method to combine pre-trained retrievers with sequence-to-sequence generators through end-to-end fine-tuning. The paradigm has evolved significantly with the advent of LLMs, shifting from joint training to modular architectures where retrieval and generation components operate independently [6].

Gao et al. [7] provide a comprehensive survey of RAG paradigms, categorizing approaches into Naive RAG, Advanced RAG, and Modular RAG. Naive RAG involves straightforward retrieval followed by generation, while Advanced RAG incorporates techniques such as query rewriting, reranking, and iterative retrieval. Modular RAG extends this further by introducing specialized components for different stages of the pipeline.

In healthcare specifically, Amugongo et al. [8] conducted a systematic review of RAG-based LLM applications, finding that proprietary models such as GPT-3.5/4 are most commonly used. The review identified a lack of standardized evaluation frameworks and noted that many studies do not adequately address ethical considerations.

### 2.3 Clinical RAG Systems

Several task-specific RAG systems have been developed for healthcare applications. ClinicalRAG [9] focuses on clinical question answering using structured knowledge graphs. BiomedRAG [10] targets biomedical literature retrieval and summarization. These systems demonstrate the potential of RAG in medical domains but are typically research prototypes with limited deployment considerations.

A common limitation across existing clinical RAG systems is their focus on specific tasks rather than providing comprehensive, general-purpose CDSS capabilities. Additionally, many systems lack detailed architectural documentation or evaluation of system-level performance metrics such as latency and scalability.

### 2.4 Research Gap

While existing research demonstrates the theoretical benefits of RAG in healthcare and provides task-specific implementations, there remains a gap in comprehensive, deployment-ready system architectures. Existing work often lacks:

- Complete end-to-end system designs that integrate frontend, backend, and database components
- Detailed architectural documentation addressing scalability and deployment considerations
- System-level evaluation metrics beyond task-specific accuracy
- Comprehensive handling of conversational context and patient-specific information
- Explicit ethical considerations and safety mechanisms

This work addresses these gaps by presenting a complete, deployment-ready CDSS architecture with comprehensive evaluation and ethical considerations.

## 3. System Architecture

### 3.1 Overview

The proposed CDSS follows a microservices architecture pattern, enabling modular development, independent scaling, and clear separation of concerns. The system consists of three primary layers: the presentation layer (frontend), the application layer (backend API), and the data layer (vector database). Figure 1 illustrates the high-level architecture.

The system architecture follows a three-tier design: (1) Presentation layer with React-based frontend for clinician interaction, (2) Application layer with FastAPI backend services handling RAG pipeline orchestration, and (3) Data layer with Qdrant vector database for semantic retrieval. External services provide embeddings and LLM generation capabilities, with support for multiple providers to enable deployment flexibility.

The architecture is designed to support horizontal scaling, with each component capable of independent deployment and scaling. Communication between components occurs through well-defined REST APIs and standard protocols, facilitating integration with existing clinical information systems.

### 3.2 Frontend Layer

The frontend is implemented using React with TypeScript, providing a responsive, clinician-focused interface. The interface supports:

- **Conversational Interaction**: A chat-based interface for natural language queries with conversation history management
- **Patient Context Management**: Upload and analysis of patient documents (PDFs, images) with OCR capabilities
- **Source Attribution**: Display of retrieved sources with citations, enabling clinicians to verify information
- **Confidence Indicators**: Visual representation of response confidence levels based on retrieval similarity scores

The frontend communicates with the backend through RESTful APIs, maintaining conversation state client-side and sending context-aware requests. The interface is designed with accessibility and usability principles, ensuring efficient interaction during clinical workflows.

### 3.3 Backend API Layer

The backend is implemented using FastAPI, a modern Python web framework that provides automatic API documentation, type validation, and asynchronous request handling. The API layer includes:

**3.3.1 Core Services**

- **Chat Service**: Handles conversational queries, managing history and context
- **Patient Service**: Processes patient document uploads, extracts text via OCR, and integrates patient context into queries
- **Admin Service**: Provides system monitoring, statistics, and knowledge base management endpoints

**3.3.2 RAG Pipeline**

The RAG pipeline orchestrates the retrieval and generation process through the following stages:

1. **Query Processing**: Receives user queries with optional conversation history and patient context
2. **Query Rewriting**: Resolves conversational references (pronouns, implicit context) to create self-contained queries
3. **Embedding Generation**: Converts queries to dense vector representations using embedding models
4. **Retrieval**: Performs semantic search against the vector database with similarity filtering
5. **Reranking**: Optionally reranks retrieved chunks using cross-encoder models for improved relevance
6. **Context Assembly**: Constructs prompts incorporating retrieved chunks, patient context, and conversation history
7. **Generation**: Generates responses using LLMs with temperature control and token limits
8. **Post-processing**: Adds source citations, confidence scores, and safety disclaimers

**3.3.3 Query Rewriting**

To handle conversational context, the system employs a query rewriting mechanism. When a user query contains pronouns or implicit references (e.g., "What are the side effects?" following a discussion about a specific medication), the system uses an LLM to rewrite the query into a self-contained form. This enables accurate retrieval even in multi-turn conversations.

**3.3.4 Adaptive Response Policies**

The system classifies queries into categories (simple, moderate, complex) and applies adaptive response policies. Simple queries receive concise responses with fewer retrieved chunks, while complex queries trigger more comprehensive retrieval and longer responses. This optimization balances response quality with latency and token usage.

### 3.4 Data Layer

**3.4.1 Vector Database**

The system uses Qdrant, an open-source vector database optimized for similarity search. Qdrant employs Hierarchical Navigable Small World (HNSW) indexing for efficient approximate nearest neighbor search, enabling sub-second retrieval even with large knowledge bases.

The vector database stores document chunks with metadata including:
- Source URL and title
- Section headings and page numbers
- Character offsets for precise citation
- Content type (HTML, PDF)
- Crawl timestamps for versioning

**3.4.2 Ingestion Pipeline**

The ingestion pipeline processes medical documents from various sources:

1. **Crawling**: Web crawler respects robots.txt and rate limits, supporting HTML and PDF content
2. **Parsing**: Specialized parsers extract text from HTML and PDF documents, preserving structure and metadata
3. **Cleaning**: Text normalization removes formatting artifacts while preserving medical terminology
4. **Chunking**: Section-aware chunking algorithm respects document structure, creating chunks at natural boundaries (headings, sections) with configurable overlap
5. **Embedding**: Chunks are embedded using dense vector models (OpenAI embeddings or local alternatives)
6. **Storage**: Embedded chunks are stored in Qdrant with metadata for retrieval and citation

The chunking strategy prioritizes semantic coherence by detecting section boundaries (headings, numbered sections) and creating chunks that preserve context. When sections exceed maximum chunk size, sliding window chunking with overlap ensures continuity.

### 3.5 External Services

The system integrates with external services for embeddings and LLM generation:

- **Embedding Providers**: Supports OpenAI embeddings or local models (e.g., all-MiniLM-L6-v2) for flexibility and cost control
- **LLM Providers**: Supports OpenAI GPT models or local alternatives (Ollama, vLLM) for generation, enabling deployment flexibility

This multi-provider approach allows institutions to choose between cloud-based services for convenience or local deployment for data privacy requirements.

## 4. Methodology

### 4.1 Knowledge Base Construction

The knowledge base is constructed from authoritative medical sources including clinical guidelines, medical journals, and institutional protocols. The ingestion process ensures:

- **Source Verification**: Only verified, authoritative sources are included
- **Version Control**: Chunks are versioned to track updates and enable rollback
- **Metadata Preservation**: Source URLs, titles, sections, and page numbers are preserved for citation

### 4.2 Retrieval Strategy

Retrieval employs semantic similarity search with the following parameters:

- **Top-K Retrieval**: Initial retrieval of K candidates (default: 40) using cosine similarity
- **Similarity Cutoff**: Filtering based on minimum similarity threshold (default: 0.22) to exclude irrelevant results
- **Reranking**: Optional cross-encoder reranking of top candidates for improved precision
- **Final Selection**: Selection of top N chunks (default: 3) for context assembly

The similarity cutoff threshold is calibrated to balance recall (ensuring relevant information is retrieved) with precision (avoiding irrelevant context that could confuse the generator).

### 4.3 Generation Strategy

Response generation follows a structured prompt template that:

1. **Establishes Role**: Defines the system as a clinical decision support assistant
2. **Provides Context**: Includes retrieved chunks with source attribution
3. **Incorporates Patient Data**: Integrates patient-specific context when available
4. **Manages History**: Includes recent conversation turns for context awareness
5. **Sets Constraints**: Explicitly instructs the model to cite sources and avoid hallucination

The system uses temperature=0.0 for deterministic, factual responses and applies token limits based on query complexity classification.

### 4.4 Safety Mechanisms

Multiple safety mechanisms are implemented:

- **Similarity Filtering**: Low-similarity retrievals trigger fallback responses indicating insufficient knowledge base coverage
- **Source Attribution**: All responses include verifiable source citations
- **Confidence Scoring**: Responses include confidence levels based on retrieval similarity
- **Legal Disclaimers**: Automatic addition of disclaimers for queries involving diagnosis or treatment recommendations
- **PII Masking**: Logging systems mask personally identifiable information

### 4.5 Patient Context Integration

When patient documents are uploaded, the system:

1. **Extracts Text**: Uses OCR (Tesseract) for images and PDF parsing for documents
2. **Stores Context**: Maintains patient context separately from the knowledge base
3. **Injects Context**: Includes patient-specific information in generation prompts while prioritizing knowledge base content for medical reasoning

This approach ensures patient data remains separate from the general knowledge base while enabling personalized responses.

## 5. Experimental Setup and Evaluation

### 5.1 Experimental Setup

**5.1.1 System Configuration**

The evaluation system was deployed using Docker Compose with the following components:
- Backend API: FastAPI service running on Python 3.11
- Vector Database: Qdrant v1.7.0 with HNSW indexing
- Frontend: React application served via Vite
- Embeddings: OpenAI text-embedding-3-small (1536 dimensions)
- LLM: GPT-4o-mini for generation

**5.1.2 Knowledge Base**

The knowledge base was populated with medical guidelines and documents totaling approximately 500 documents, resulting in approximately 15,000 chunks after processing. Documents included clinical guidelines, medical reference materials, and institutional protocols.

**5.1.3 Evaluation Queries**

A set of 50 diverse clinical queries was constructed covering:
- Diagnostic questions (e.g., "What are the diagnostic criteria for hypertension?")
- Treatment inquiries (e.g., "What are first-line treatments for type 2 diabetes?")
- Drug information (e.g., "What are the contraindications for metformin?")
- General medical knowledge (e.g., "Explain the mechanism of action of ACE inhibitors")

### 5.2 Evaluation Metrics

**5.2.1 Retrieval Metrics**

- **Retrieval Latency**: Time from query submission to retrieval completion (target: <500ms)
- **Retrieval Precision**: Proportion of retrieved chunks relevant to the query (evaluated manually)
- **Coverage**: Proportion of queries for which relevant information was retrieved

**5.2.2 Generation Metrics**

- **Response Relevance**: Manual evaluation of whether responses address the query (binary: relevant/not relevant)
- **Source Attribution**: Presence and accuracy of source citations
- **Hallucination Detection**: Manual review for unsupported claims or factual errors
- **Generation Latency**: End-to-end time from query to response (target: <3 seconds)

**5.2.3 System Metrics**

- **Throughput**: Queries processed per second under load
- **Error Rate**: Proportion of queries resulting in system errors

### 5.3 Results

**5.3.1 Retrieval Performance**

The retrieval system achieved:
- Average retrieval latency: 342ms (std: 89ms)
- Retrieval precision: 78% of retrieved chunks were relevant (evaluated on 200 query-chunk pairs)
- Coverage: 94% of queries retrieved at least one relevant chunk

The similarity cutoff threshold of 0.22 effectively filtered irrelevant results while maintaining high recall. Reranking improved precision for complex queries but added approximately 200ms latency.

**5.3.2 Generation Performance**

Response generation results:
- Average end-to-end latency: 2.1 seconds (std: 0.6s)
- Response relevance: 92% of responses were judged relevant to queries
- Source attribution: 100% of responses included at least one source citation
- Hallucination rate: 4% of responses contained unsupported claims (detected through manual review)

The query rewriting mechanism improved retrieval accuracy for conversational queries by 15% compared to using raw queries.

**5.3.3 System Performance**

Under moderate load (10 concurrent requests):
- Throughput: 4.2 queries/second
- Error rate: 1.2% (primarily timeout errors under high load)
- System remained stable with response times within acceptable ranges

**5.3.4 Qualitative Analysis**

Manual review of responses revealed:
- Responses were generally well-structured and cited sources appropriately
- Patient context integration improved personalization when relevant
- Confidence scores correlated with response quality (high confidence responses were more accurate)
- Some responses were overly verbose for simple queries, indicating potential for further optimization

### 5.4 Discussion

The evaluation results demonstrate that the proposed architecture achieves practical performance levels suitable for clinical deployment. Retrieval latency under 500ms enables near-real-time interaction, while the 92% relevance rate indicates effective grounding in the knowledge base.

The 4% hallucination rate, while lower than baseline LLM performance, highlights the importance of continued monitoring and refinement. The similarity cutoff and source attribution mechanisms contribute to this improvement, but further enhancements may be possible through more sophisticated reranking or post-generation verification.

The system's modular architecture facilitated evaluation and optimization of individual components. The ability to switch between embedding and LLM providers enabled cost-performance trade-offs and deployment flexibility.

Limitations of the evaluation include:
- The knowledge base size (15,000 chunks) is smaller than production deployments might require
- Evaluation queries were constructed rather than collected from real clinical use
- Manual evaluation introduces subjectivity, though inter-annotator agreement was not formally measured

## 6. Limitations and Ethical Considerations

### 6.1 Technical Limitations

**6.1.1 Knowledge Base Coverage**

The system's effectiveness is constrained by the scope and quality of its knowledge base. Gaps in coverage may result in incomplete or unavailable information for certain queries. The system addresses this through explicit fallback messages, but clinicians must be aware of these limitations.

**6.1.2 Retrieval Accuracy**

While semantic similarity search is effective for many queries, it may struggle with highly specialized terminology, rare conditions, or queries requiring complex reasoning across multiple documents. The similarity cutoff, while necessary, may exclude relevant information in edge cases.

**6.1.3 Context Window Limitations**

LLM context windows limit the amount of retrieved information that can be included in generation prompts. For complex queries requiring extensive context, the system must prioritize the most relevant chunks, potentially missing important information.

**6.1.4 Latency Considerations**

While the system achieves sub-3-second response times in most cases, network latency, database load, and LLM API response times can introduce variability. Real-time clinical scenarios may require further optimization or caching strategies.

### 6.2 Ethical Considerations

**6.2.1 Clinical Decision Support, Not Replacement**

This system is designed as a decision support tool to assist clinicians, not replace their judgment. All outputs must be verified by qualified healthcare professionals. The system explicitly disclaims diagnostic or treatment recommendations and emphasizes the need for professional clinical judgment.

**6.2.2 Data Privacy and Security**

The system processes patient documents and clinical queries, which may contain sensitive health information. Implementation must comply with healthcare data protection regulations (e.g., HIPAA in the United States, GDPR in Europe). The architecture supports local deployment to maintain data within institutional boundaries, but proper access controls, encryption, and audit logging are essential.

**6.2.3 Bias and Fairness**

Medical knowledge bases may reflect biases present in source materials, potentially affecting response quality across different patient populations or conditions. The system's retrieval mechanism does not explicitly address bias mitigation, representing an area for future improvement.

**6.2.4 Transparency and Explainability**

The system provides source citations to enhance transparency, but the reasoning process of the LLM generator remains opaque. Clinicians should understand that responses are generated based on retrieved context but may not fully explain the model's internal reasoning.

**6.2.5 Accountability**

Clear accountability structures are necessary when AI systems are integrated into clinical workflows. The system logs queries and responses for audit purposes, but institutional policies must define responsibility for system outputs and error handling.

**6.2.6 Validation Requirements**

Before deployment in real clinical settings, the system requires:
- Clinical validation studies to assess impact on decision-making and patient outcomes
- Regulatory review as appropriate for medical device software
- Integration testing with existing clinical information systems
- Training for end users on system capabilities and limitations

### 6.3 Responsible Deployment

To ensure responsible deployment, we recommend:

1. **Pilot Testing**: Initial deployment in non-critical scenarios with close monitoring
2. **Continuous Monitoring**: Ongoing evaluation of response quality, error rates, and user feedback
3. **Regular Updates**: Knowledge base updates to incorporate latest guidelines and research
4. **User Training**: Education for clinicians on interpreting system outputs and recognizing limitations
5. **Incident Reporting**: Mechanisms for reporting errors, biases, or safety concerns
6. **Version Control**: Tracking of system versions and knowledge base updates for reproducibility

## 7. Conclusion and Future Work

This paper presented the design, implementation, and evaluation of an end-to-end AI Clinical Decision Support System using Retrieval-Augmented Generation. The system addresses key limitations of LLMs in healthcare through semantic retrieval, source attribution, and safety mechanisms, while providing a practical, deployment-ready architecture.

The modular microservices design enables scalability, maintainability, and integration with existing clinical systems. Evaluation results demonstrate that the system achieves practical performance levels with sub-second retrieval and sub-3-second end-to-end response times, while maintaining high response relevance and low hallucination rates.

The work contributes a comprehensive architectural blueprint that bridges the gap between algorithmic RAG research and practical deployment. By detailing component design, integration patterns, and evaluation methodologies, this paper provides a foundation for future development and refinement of AI-powered CDSS.

### 7.1 Future Work

Several directions for future research and development are identified:

**7.1.1 Enhanced Retrieval**

- **Multi-hop Reasoning**: Extending retrieval to support complex queries requiring reasoning across multiple documents
- **Temporal Reasoning**: Incorporating temporal information to prioritize recent guidelines or account for guideline updates
- **Specialized Embeddings**: Fine-tuning embedding models on medical corpora to improve domain-specific retrieval accuracy

**7.1.2 Improved Generation**

- **Fact Verification**: Post-generation verification mechanisms to detect and correct hallucinations
- **Response Summarization**: Adaptive summarization for verbose responses while preserving critical information
- **Multi-modal Support**: Integration of image analysis for radiology, pathology, and other visual medical data

**7.1.3 Evaluation and Validation**

- **Clinical Validation Studies**: Real-world evaluation of system impact on clinical decision-making and patient outcomes
- **Standardized Benchmarks**: Development of standardized evaluation datasets and metrics for clinical RAG systems
- **Longitudinal Studies**: Assessment of system performance over time as knowledge bases evolve

**7.1.4 Ethical and Safety Enhancements**

- **Bias Mitigation**: Techniques to identify and mitigate biases in knowledge bases and retrieval mechanisms
- **Explainability**: Enhanced explainability features to provide clearer reasoning traces for system outputs
- **Adversarial Testing**: Systematic testing for adversarial inputs and edge cases

**7.1.5 Integration and Deployment**

- **EHR Integration**: Direct integration with Electronic Health Record systems for seamless workflow integration
- **Multi-institutional Deployment**: Support for federated knowledge bases across multiple institutions
- **Real-time Updates**: Mechanisms for real-time knowledge base updates as new guidelines are published

The field of AI-powered clinical decision support is rapidly evolving, and this work represents one step toward safe, effective, and responsible deployment of these technologies in healthcare settings. Continued collaboration between AI researchers, clinicians, and healthcare institutions will be essential to realize the full potential of RAG-based CDSS while ensuring patient safety and clinical effectiveness.

## References

[1] Sutton, R.T., et al.: An overview of clinical decision support systems: benefits, risks, and strategies for success. NPJ Digit. Med. 3, 17 (2020). https://doi.org/10.1038/s41746-020-0221-y

[2] Rajkomar, A., Dean, J., Kohane, I.: Machine learning in medicine. N. Engl. J. Med. 380(14), 1347-1358 (2019). https://doi.org/10.1056/NEJMra1814259

[3] Ji, Z., et al.: Survey of hallucination in natural language generation. ACM Comput. Surv. 55(12), 1-38 (2023). https://doi.org/10.1145/3571730

[4] Singhal, K., et al.: Large language models encode clinical knowledge. Nature 620(7972), 172-180 (2023). https://doi.org/10.1038/s41586-023-06291-2

[5] Lewis, P., et al.: Retrieval-augmented generation for knowledge-intensive NLP tasks. In: Advances in Neural Information Processing Systems, vol. 33, pp. 9459-9474 (2020)

[6] Gao, Y., et al.: Retrieval-augmented generation for large language models: a survey. arXiv preprint arXiv:2312.10997 (2023)

[7] Gao, Y., et al.: Retrieval-augmented generation for large language models: a survey. arXiv preprint arXiv:2312.10997 (2023)

[8] Amugongo, L.M., et al.: Retrieval augmented generation for large language models in healthcare: a systematic review. PLOS Digit. Health 4(6), e0000877 (2025). https://doi.org/10.1371/journal.pdig.0000877

[9] Lu, Y., et al.: ClinicalRAG: Enhancing clinical decision support through heterogeneous knowledge retrieval. In: Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (2024)

[10] Li, M., et al.: BiomedRAG: A retrieval augmented large language model for biomedicine. arXiv preprint arXiv:2405.00465 (2024)

[11] OpenAI: GPT-4 technical report. arXiv preprint arXiv:2303.08774 (2023)

[12] Touvron, H., et al.: LLaMA: Open and efficient foundation language models. arXiv preprint arXiv:2302.13971 (2023)

[13] Lee, J., et al.: BioBERT: a pre-trained biomedical language representation model for biomedical text mining. Bioinformatics 36(4), 1234-1240 (2020). https://doi.org/10.1093/bioinformatics/btz682

[14] Alsentzer, E., et al.: Publicly available clinical BERT embeddings. arXiv preprint arXiv:1904.03323 (2019)

[15] Singhal, K., et al.: Large language models encode clinical knowledge. Nature 620(7972), 172-180 (2023). https://doi.org/10.1038/s41586-023-06291-2

[16] Singhal, K., et al.: Towards expert-level medical question answering with large language models. arXiv preprint arXiv:2305.09617 (2023)

[17] Shetty, V.B.: Retrieval-augmented generation (RAG) with LLMs: architecture, methodology, system design, limitations, and outcomes. In: Proceedings of the International Conference on Machine Learning Applications (2025)

[18] Nouis, S.C.E., et al.: Evaluating accountability, transparency, and bias in AI-assisted healthcare decision-making: a qualitative study of healthcare professionals' perspectives in the UK. BMC Med. Ethics 26, 12 (2025). https://doi.org/10.1186/s12910-025-01243-z

