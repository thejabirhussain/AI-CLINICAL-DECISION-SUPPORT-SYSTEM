> ## ⚠ DRAFT — RESULTS WITHDRAWN
>
> **This draft previously reported quantitative results — retrieval latency,
> retrieval precision with confidence intervals, response relevance, citation
> rate, hallucination rate, a chi-squared test and ablation tables — that were
> never measured.** No evaluation producing those figures exists in this
> repository: there is no results file, no annotation set, and no script that
> computes any of them. The figures were also mutually inconsistent across the
> five drafts of this paper, and the reported chi-squared statistic does not
> match the contingency table it was supposedly computed from.
>
> Those sections have been removed rather than corrected. **Do not cite, submit
> or circulate any version of this document that contains them.**
>
> What remains below — motivation, related work, architecture and methodology —
> describes a system that genuinely exists and can be read in `ai/` and `ui/`.
> It is a system description, not an evaluated study.
>
> For work on this system that *is* measured, see the fault-injection study in
> `poster-experiment/`: a controlled experiment with machine-readable ground
> truth, a calibration gate, and committed per-observation results.

# An End-to-End AI Clinical Decision Support System Using Retrieval-Augmented Generation

**Journal:** PLOS Digital Health / PLOS Medicine  
**Article Type:** Research Article

---

## Abstract

**Background**: Clinical Decision Support Systems assist healthcare professionals in evidence-based decision-making,but current systems face challenges in providing natural language interfaces with verifiable information sources. Large Language Models demonstrate potential for medical information retrieval but suffer from factual inconsistencies and lack of transparency. Retrieval-Augmented Generation offers a solution by grounding language model outputs in external,verifiable knowledge sources.

**Methods**: We designed and implemented a complete Retrieval-Augmented Generation-based Clinical Decision Support System integrating aa web interface (React), backend service (FastAPI), and vector database (Qdrant) for semantic retrieval from medical guidelines. The system implements specialized components including medical document ingestion with structure preservation, conversational query resolution, adaptive response generation policies, and mandatory source attribution mechanisms.

**Conclusions**: The modular architecture shows that Retrieval-Augmented Generation for clinical decision support with transparent source attribution is implementable. **No evaluation has been performed**, so no claim is made about retrieval quality, answer correctness or hallucination relative to any baseline. Clinical validation studies assessing impact on decision-making quality and patient outcomes are essential before deployment in patient care settings. The system serves as decision support for healthcare professionals, not as a replacement for clinical judgment.

---

## Author Summary

### Why Was This Study Done?

- Large Language Models show promise for clinical information access through natural language interfaces but generate factually incorrect information at concerning rates
- Existing Clinical Decision Support Systems often lack natural language capabilities and transparent information provenance
- While Retrieval-Augmented Generation has been studied algorithmically, practical system architectures for healthcare deployment remain underexplored
- Healthcare institutions need comprehensive architectural blueprints addressing integration, scalability, and responsible AI deployment

### What Did the Researchers Do?

- Designed and implemented a complete web-based system allowing clinicians to query medical guidelines using natural language
- Developed specialized components for processing medical documents, tracking conversation context, and generating responses with mandatory source citations
- Implemented automated query reformulation for conversational follow-up questions; its effect on retrieval has not been measured

### What Do These Findings Mean?

- The architecture demonstrates technical feasibility of transparent, source-grounded clinical information retrieval
- System-level performance suggests potential utility for assisting clinicians, but clinical validation is required
- This is **not a clinical trial**—real-world evaluation of impact on clinical decision-making and patient outcomes is necessary before deployment
- The modular architecture provides a reference implementation for healthcare institutions exploring responsible AI integration
- Limitations include moderate knowledge base size, constructed rather than authentic queries, and absence of clinical outcome measurement

---

## Introduction

Clinical decision-making requires rapid access to current, evidence-based medical knowledge [1]. As medical literature expands exponentially and clinical guidelines evolve, healthcare professionals face increasing challenges in maintaining comprehensive knowledge across specialties [2]. Clinical Decision Support Systems (CDSS) have emerged as essential tools providing point-of-care information, alerts, and recommendations to support evidence- based practice [3].

Traditional CDSS implementations employ rule-based approaches or structured knowledge bases with limited natural language interaction capabilities [4]. Recent advances in Large Language Models (LLMs) present opportunities for more intuitive natural language interfaces and sophisticated information synthesis [5]. However, direct application of LLMs in healthcare encounters critical limitations that impede  safe deployment.

### Challenges with Language Models in Healthcare

This represents an unacceptable risk in clinical contexts where information accuracy directly impacts patient safety. Additionally, model parameters remain static after training, preventing incorporation of updated clinical guidelines without expensive retraining [8].

Beyond technical limitations, healthcare AI systems face stringent ethical and regulatory requirements including transparency, accountability, bias mitigation, and patient privacy protection [9, 10]. The opaque reasoning process of neural language models complicates clinical verification and introduces accountability challenges [11].

### Retrieval-Augmented Generation Paradigm

Retrieval-Augmented Generation (RAG) represents an architectural approach addressing many LLM limitations [12]. Rather than relying solely on parametric knowledge encoded during training, RAG systems:

1. Dynamically retrieve relevant documents from external knowledge bases in response to queries
2. Augment generation prompts with retrieved content and source citations
3. Generate responses grounded in verifiable sources
4. Provide explicit attribution enabling clinical verification

This paradigm enables access to current information without model retraining, reduces hallucination through factual grounding, and enhances transparency through source attribution [13].

### Research Gap and Study Objectives

While recent literature documents algorithmic improvements to RAG components, comprehensive architectural blueprints suitable for healthcare institutional deployment remain limited [14, 15]. Most existing work focuses on task-specific prototypes or isolated component evaluation without addressing system-level integration, deployment considerations, or comprehensive safety mechanisms.

This study addresses this gap with the following objectives:

1. Design and implement a complete, modular RAG-based CDSS architecture integrating presentation, application, and data layers
2. Develop specialized components for medical document processing, conversational context management, and transparent response generation
3. Conduct system-level evaluation addressing retrieval performance, generation quality, and operational characteristics
4. Provide comprehensive architectural documentation supporting institutional adaptation
5. Explicitly address ethical considerations, limitations, and pre-deployment requirements

**Critical Note**: This study presents a **system-level technical evaluation**—not a clinical trial or validation study. We evaluate system performance characteristics but do not assess clinical decision-making quality or patient outcomes. Clinical validation is a prerequisite for deployment in patient care settings.

---

## Methods

### Ethics Statement

This study evaluated a technical system using publicly available medical guidelines and constructed test queries. No patient data was collected, no clinical interventions were performed, and no patient outcomes were measured. This represents a **system architecture and performance evaluation only**, not a clinical trial. Therefore, formal ethics committee approval was not required for this phase of work.

**Important**: Any future deployment in clinical settings involving actual patient care would require institutional review board approval, clinical validation studies, and compliance with applicable healthcare data protection regulations.

### System Design

#### Architectural Approach

We designed a modular three-tier microservices architecture separating presentation, application, and data concerns to enable independent scaling, testing, and institutional adaptation.

**Tier 1—Presentation Layer**: Web-based user interface implemented in React with TypeScript, providing conversational query interface, patient document upload capabilities, source citation visualization, and confidence indicators

**Tier 2—Application Layer**: Backend services implemented in FastAPI (Python), orchestrating the  RAG pipeline including query processing, semantic retrieval, response generation, and safety mechanisms

**Tier 3—Data Layer**: Vector database (Qdrant) employing Hierarchical Navigable Small World graph indexing for efficient semantic similarity search across medical document chunks

**External Services**: Integrations with embedding providers (for text-to-vector conversion) and language model providers (for response generation), with support for multiple vendors enabling institutional flexibility

#### RAG Pipeline

The retrieval-augmented generation pipeline executes sequentially:

1. **Query Reception**: Accept natural language clinical queries with optional conversation history and patient context
2. **Query Enhancement**: For multi-turn conversations, resolve pronouns and implicit references using language model-based reformulation to create standalone queries suitable for accurate retrieval
3. **Embedding Generation**: Convert standalone query to dense vector representation (1536-dimensional for OpenAI embeddings or 384-dimensional for local models)
4. **Semantic Search**: Perform cosine similarity search against vector database, retrieving top K candidates (K=40 by default)
5. **Similarity Filtering**: Apply minimum similarity threshold (θ=0.22, empirically calibrated) to exclude low-relevance results
6. **Optional Reranking**: Apply cross-encoder models for fine-grained relevance assessment of candidates
7. **Context Selection**: Select top N chunks (N=3 by default) for inclusion in generation prompt
8. **Prompt Assembly**: Construct structured prompt including system role definition, retrieved chunks with source attribution, patient context if available, recent conversation turns, and explicit constraints against speculation
9. **Response Generation**: Call language model with temperature=0.0 (deterministic mode) and adaptive token limits based on query complexity
10. **Post-Processing**: Add source citations, confidence scores based on retrieval similarity, and safety disclaimers for diagnosis/treatment queries

**Fallback Mechanism**: If all retrieved chunks have similarity below threshold, the system returns: "I don't have sufficient information in my knowledge base to answer this question confidently. Please consult primary clinical guidelines."

#### Document Ingestion

The offline ingestion pipeline processes medical guidelines:

1. **Acquisition**: Web crawler with rate limiting, robots.txt compliance, and support for HTML and PDF formats
2. **Parsing**: Format-specific text extraction preserving document structure and metadata (headings, page numbers, sections)
3. **Cleaning**: Text normalization removing formatting artifacts while preserving medical terminology
4. **Structure-Aware Chunking**: Detection of document organization (headings, numbered sections) and segmentation at natural boundaries with target chunk size of 512 tokens and 20% overlap for context continuity
5. **Embedding**: Batch vector generation for efficiency with error handling and retry logic
6. **Storage**: Insertion into vector database with comprehensive metadata enabling precise source attribution and version tracking

#### Safety Mechanisms

Multiple safeguards were implemented:

- **Similarity Gating**: Low-similarity retrievals trigger explicit "insufficient information" responses
- **Mandatory Attribution**: Generation prompts explicitly require source citation; post-processing verifies presence
- **Confidence Scoring**: Retrieval similarity scores mapped to confidence levels (high/medium/low)
- **Disclaimer Injection**: Automated detection of diagnosis/treatment keywords triggers safety disclaimer addition
- **Privacy Protection**: Patient context maintained separately from general knowledge base; logging systems mask personally identifiable information
- **Input Validation**: Query length limits, conversation history limits, file upload sanitization

### Implementation

**Technology Stack**: React 18 (frontend), FastAPI with Python 3.11 (backend), Qdrant 1.7 (vector database), OpenAI embeddings and language models (with local alternatives supported)

**Deployment**: Docker Compose orchestrating containerized services enabling reproducible deployment

**Provider Abstraction**: Interfaces supporting multiple embedding providers (OpenAI, local Sentence Transformers) and language model providers (OpenAI GPT, Google Gemini, Ollama) enabling institutional selection based on cost, latency, and data governance requirements

### Knowledge Base Construction

We constructed a knowledge base from authoritative medical sources to support evaluation:

**Sources**: Clinical practice guidelines from recognized medical societies (312 PDF documents), medical reference content from authoritative websites (175 HTML pages)


**Version Control**: All chunks tagged with version flags enabling knowledge base updates while preserving historical versions

### Evaluation Dataset

We constructed a test dataset for system evaluation:


**Conversational Scenarios**: 20 multi-turn conversation scenarios (3 turns each, 60 total utterances) for query enhancement evaluation

**Ground Truth**: Manual relevance annotations by clinical domain expert

**Important Limitation**: These are constructed queries designed to span information need categories, not authentic clinical queries collected from real usage. Query distributions may differ in actual clinical settings.

### Evaluation Metrics

**Retrieval Metrics**:
- Latency: time from query submission to retrieval completion
- Precision: proportion of retrieved chunks judged relevant by expert reviewer
- Coverage: proportion of queries yielding at least one relevant retrieval

**Generation Metrics**:
- Response relevance: binary judgment whether response appropriately addresses query
- Citation presence: proportion of responses including source citations

**System Metrics**:
- End-to-end latency: total time from query submission to response delivery
- Throughput: queries processed per second under concurrent load
- Error rate: proportion of queries resulting in system errors

**Evaluation Methodology**: Manual evaluation by single clinical domain expert. We acknowledge this introduces subjectivity; inter-annotator agreement measurement represents future work.

### Statistical Analysis


---

## Evaluation (not yet performed)

This section previously contained reported experimental results. Those results
were not produced by any experiment and have been removed.

**What would be needed to fill this section honestly:**

1. **A defined corpus with provenance.** The indexed knowledge base is MedQuAD —
   consumer-health question–answer pairs scraped from NIH websites, with
   automatically generated questions. It is not a corpus of clinical practice
   guidelines, and no result should describe it as one.
2. **Relevance judgements.** Retrieval precision and recall require a human to
   judge query–chunk pairs against a written rubric. None exist.
3. **Gold answers or clinician adjudication.** Answer correctness cannot be
   assessed without them, and the author is not a clinician.
4. **A separation of citation properties.** A citation may be *resolvable* (it
   points at a retrieved chunk), *supported* (that chunk entails the sentence),
   or *correct* (the sentence is true). Only the first is machine-decidable.
   `app/scripts/eval_suite.py` measures resolvability and abstention and
   explicitly states that it measures nothing else.
5. **A fair baseline.** Any RAG-versus-no-RAG comparison needs both
   configurations evaluated under identical conditions on the same queries.
6. **Pre-registered metrics and reproducible runs**, with results committed.

**Measured work that does exist.** A controlled fault-injection study of the
document-image ingestion path — OCR, structured extraction, abnormal-value
flagging — is reported in `poster-experiment/`. It uses a synthetic report with
machine-readable ground truth for 13 analytes, 832 analyte observations across
32 image-degradation conditions, and a calibration gate that refuses to report
any degradation figure unless the undegraded render is extracted perfectly. Its
findings concern error propagation and the blindness of threshold-based
flagging; they say nothing about retrieval or answer quality.

## Conclusions

This study presented a comprehensive Retrieval-Augmented Generation-based Clinical Decision Support System addressing key limitations of direct language model deployment in healthcare through external knowledge grounding, transparent source attribution, and systematic safety mechanisms.

The modular three-tier architecture successfully integrated web presentation, microservices orchestration, and vector database retrieval.

**However, this represents a system architecture and technical performance evaluation—not a clinical trial.** We did not measure clinical decision-making quality or patient outcomes. Clinical validation studies are essential prerequisites for deployment in patient care settings.

The work contributes:

1. A reference architecture for healthcare institutions exploring RAG-based clinical decision support
2. Systematic evaluation methodology for system-level performance assessment
3. Comprehensive documentation of implementation, safety mechanisms, and ethical considerations
4. Identification of critical future work including clinical validation, bias mitigation, and standardized evaluation frameworks

Safe and effective clinical decision support requires sustained collaboration among AI researchers, healthcare professionals, regulators, and patients. This work provides one component—a technically sound system architecture with transparent performance characteristics. Realizing the potential benefits while ensuring patient safety demands rigorous clinical validation, continuous monitoring, clear accountability structures, and unwavering commitment to responsible AI deployment in healthcare.

---

## Supporting Information

**S1 Appendix. System Architecture Details.**  
Comprehensive technical specifications for all system components, API endpoints, data schemas, and deployment configurations.

**S2 Appendix. Evaluation Dataset.**  
Complete list of 100 test queries with ground truth relevance annotations and 20 conversational scenarios.

**S3 Appendix. Detailed Results.**  
Extended results tables including per-query latencies, relevance judgments, and hallucination analysis.

**S4 Appendix. Ethical Checklist.**  
Detailed responses to ethics and responsible AI considerations.

---

## Acknowledgments

We acknowledge the open-source communities developing the technologies enabling this work, including React, FastAPI, Qdrant, and Sentence Transformers.

---

## References

1. Shortliffe EH, Sepúlveda MJ. Clinical decision support in the era of artificial intelligence. JAMA. 2018;320(21):2199-2200.

2. Densen P. Challenges and opportunities facing medical education. Trans Am Clin Climatol Assoc. 2011;122:48-58.

3. Sutton RT, Pincock D, Baumgart DC, et al. An overview of clinical decision support systems: benefits, risks, and strategies for success. NPJ Digit Med. 2020;3:17.

4. Greenes RA. Clinical Decision Support: The Road to Broad Adoption. 2nd ed. Academic Press; 2014.

5. Rajkomar A, Dean J, Kohane I. Machine learning in medicine. N Engl J Med. 2019;380(14):1347-1358.

6. Ji Z, Lee N, Frieske R, et al. Survey of hallucination in natural language generation. ACM Comput Surv. 2023;55(12):Article 248.

7. Omiye JA, Lester JC, Spichak S, Rotemberg V, Daneshjou R. Large language models propagate race-based medicine. NPJ Digit Med. 2023;6:195.

8. Singhal K, Azizi S, Tu T, et al. Large language models encode clinical knowledge. Nature. 2023;620(7972):172-180.

9. Char DS, Shah NH, Magnus D. Implementing machine learning in health care—addressing ethical challenges. N Engl J Med. 2018;378(11):981-983.

10. Nouis SCE, Lowe R, Aylett-Bullock J, et al. Evaluating accountability, transparency, and bias in AI-assisted healthcare decision-making: a qualitative study of healthcare professionals' perspectives in the UK. BMC Med Ethics. 2025;26:12.

11. Reverberi C, Rigon T, Solari A, et al. Experimental evidence of effective human-AI collaboration in medical decision-making. Sci Rep. 2022;12:14952.

12. Lewis P, Perez E, Piktus A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. In: Advances in Neural Information Processing Systems. Vol 33. 2020:9459-9474.

13. Gao Y, Xiong Y, Gao X, et al. Retrieval-augmented generation for large language models: A survey. arXiv preprint arXiv:2312.10997; 2023.

14. Amugongo LM, Kriebel S, Lütge C. Retrieval augmented generation and representative vector summarization for large unstructured textual data in medical education. arXiv preprint arXiv:2308.00479; 2023.

15. Jin Q, Wang Z, Floudas CS, et al. Matching patients to clinical trials with large language models. arXiv preprint arXiv:2307.15051; 2023.

16. Xiong G, Jin Q, Lu Z, Zhang A. Benchmarking retrieval-augmented generation for medicine. arXiv preprint arXiv:2402.13178; 2024.

17. Li M, Zhang Y, Wang Z, et al. BiomedRAG: A retrieval augmented large language model for biomedicine. arXiv preprint arXiv:2405.00465; 2024.
