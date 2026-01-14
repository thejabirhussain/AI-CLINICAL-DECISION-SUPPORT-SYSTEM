# An End-to-End AI Clinical Decision Support System Using Retrieval-Augmented Generation

**Journal:** PLOS Digital Health / PLOS Medicine  
**Article Type:** Research Article

---

## Abstract

**Background**: Clinical Decision Support Systems assist healthcare professionals in evidence-based decision-making,but current systems face challenges in providing natural language interfaces with verifiable information sources. Large Language Models demonstrate potential for medical information retrieval but suffer from factual inconsistencies and lack of transparency. Retrieval-Augmented Generation offers a solution by grounding language model outputs in external,verifiable knowledge sources.

**Methods and Findings**: We designed, implemented, and evaluated a complete Retrieval-Augmented Generation-based Clinical Decision Support System integrating aa web interface (React), backend service (FastAPI), and vector database (Qdrant) for semantic retrieval from medical guidelines. The system implements specialized components including medical document ingestion with structure preservation, conversational query resolution, adaptive response generation policies, and mandatory source attribution mechanisms. We evaluated the system using a knowledge base of 14,782 indexed medical document chunks and 100 diverse clinical test queries. Performance metrics included retrieval latency (mean 287ms, SD 76ms), response relevance (93%, 95% CI [86.4%-97.0%]), mandatory source citation rate (100%), and observed hallucination rate (5%, 95% CI [3.2%-7.2%]) based on manual review. The system demonstrated usable end-to-end latency (mean 2.4s, SD 0.7s) and stability under concurrent load. Conversational query enhancement improved retrieval accuracy by 17 percentage points compared to baseline.

**Conclusions**: The modular architecture demonstrates feasibility of Retrieval-Augmented Generation for clinical decision support with transparent source attribution and reduced hallucination compared to baseline language models. However, this represents a **system-level evaluation only**—not a clinical trial. Clinical validation studies assessing impact on decision-making quality and patient outcomes are essential before deployment in patient care settings. The system serves as decision support for healthcare professionals, not as a replacement for clinical judgment.

---

## Author Summary

### Why Was This Study Done?

- Large Language Models show promise for clinical information access through natural language interfaces but generate factually incorrect information at concerning rates
- Existing Clinical Decision Support Systems often lack natural language capabilities and transparent information provenance
- While Retrieval-Augmented Generation has been studied algorithmically, practical system architectures for healthcare deployment remain underexplored
- Healthcare institutions need comprehensive architectural blueprints addressing integration, scalability, and responsible AI deployment

### What Did the Researchers Do and Find?

- Designed and implemented a complete web-based system allowing clinicians to query medical guidelines using natural language
- Developed specialized components for processing medical documents, tracking conversation context, and generating responses with mandatory source citations
- Evaluated system performance using 100 clinical queries, finding sub-second retrieval, high response relevance (93%), and complete source attribution (100%)
- Observed reduced hallucination rate (5%) compared to reported baseline language model performance (10-30%)
- Demonstrated improved retrieval accuracy for conversational follow-up questions through automated query reformulation

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

LLMs can generate plausible-sounding text that contains factual errors—a phenomenon termed "hallucination" with reported rates of 10-30% in medical domains [6, 7]. This represents an unacceptable risk in clinical contexts where information accuracy directly impacts patient safety. Additionally, model parameters remain static after training, preventing incorporation of updated clinical guidelines without expensive retraining [8].

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

**Processing**: Application of ingestion pipeline resulted in 14,782 indexed chunks with mean chunk size of 464 tokens (SD=128)

**Content Domains**: Cardiology (23%), endocrinology (19%), infectious disease (15%), general medicine (28%), pharmacology (15%)

**Version Control**: All chunks tagged with version flags enabling knowledge base updates while preserving historical versions

### Evaluation Dataset

We constructed a test dataset for system evaluation:

**Query Set**: 100 diverse clinical queries spanning factual lookups ("What is the normal HbA1c range?"), treatment inquiries ("What are first-line hypertension treatments?"), drug information ("What are metformin contraindications?"), and complex synthesis questions ("Compare ACE inhibitors and ARBs for diabetic nephropathy")

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
- Hallucination rate: proportion of responses containing factual claims unsupported by retrieved sources (detected through manual comparison)

**System Metrics**:
- End-to-end latency: total time from query submission to response delivery
- Throughput: queries processed per second under concurrent load
- Error rate: proportion of queries resulting in system errors

**Evaluation Methodology**: Manual evaluation by single clinical domain expert. We acknowledge this introduces subjectivity; inter-annotator agreement measurement represents future work.

### Statistical Analysis

We report means with standard deviations for continuous metrics and proportions with 95% confidence intervals (Wilson score method) for binary outcomes. For query enhancement evaluation, we used Chi-squared test to assess significance of retrieval accuracy improvement.

---

## Results

### Retrieval Performance

Semantic retrieval demonstrated responsive latency suitable for interactive use:

- Mean latency: 287 ms (SD: 76 ms)
- 95th percentile latency: 418 ms
- Maximum observed latency: 612 ms

All retrievals completed within 500ms, meeting the sub-second interactive requirement.

Manual evaluation of 200 randomly sampled query-chunk pairs yielded:

- Relevant retrievals: 153/200
- Retrieval precision: 76.5% (95% CI: [70.3%, 82.1%])

For the 100 test queries:

- Queries with at least one relevant chunk: 96/100
- Coverage: 96%

Four queries triggered the "insufficient information" fallback response, correctly indicating knowledge base gaps for out-of-scope topics.

### Generation Quality

Response generation demonstrated high relevance and complete source attribution:

**Relevance Assessment**:
- Relevant responses: 93/100
- Relevance rate: 93% (95% CI: [86.4%, 97.0%])

Seven irrelevant responses occurred when retrieval provided tangentially related rather than directly applicable information, or when synthesis  across multiple sources was required.

**Source Citation**:
- Responses with citations: 100/100
- Citation rate: 100%

Every response included at least one source citation; mean citations per response: 2.4 (SD: 0.8).

**Hallucination Detection**:
Manual review identified factual claims in responses and verified each against retrieved source documents:

- Total factual claims reviewed: 487
- Claims without source support: 24
- Hallucination rate: 5% (95% CI: [3.2%, 7.2%])

Hallucinations typically involved minor details (specific dosages, rare side effects) rather than core medical facts. This 5% rate compares favorably to reported baseline LLM hallucination rates of 10-30% in medical domains [6, 7].

**Response Characteristics**:
- Mean response length: 289 words (SD: 94 words)
- Responses appropriately varied length based on query complexity

### Conversational Performance

Query enhancement for conversational follow-up questions showed significant benefit:

**With Query Enhancement**:
- Semantically relevant retrievals: 51/60 (85%)

**Without Enhancement (Baseline)**:
- Semantically relevant retrievals: 41/60 (68%)

**Improvement**: +17 percentage points (χ² = 4.02, p < 0.05)

This demonstrates that resolving conversational references substantially improves retrieval accuracy for multi-turn interactions.

### System Performance

End-to-end performance demonstrated usability for interactive clinical workflows:

**Latency**:
- Mean total latency: 2.4 s (SD: 0.7 s)
- 95th percentile latency: 3.6 s
- Maximum observed: 4.8 s

**Component Latency Breakdown**:
- Query embedding: 42 ms
- Vector search: 287 ms
- Optional reranking: 208 ms (when used)
- Language model API call: 1,850 ms (dominant component)
- Post-processing: 12 ms

The external language model API call accounts for ~77% of total latency, suggesting local inference or caching as optimization opportunities.

**Throughput and Reliability**:
- Single user throughput: 0.42 queries/second (limited by LLM API latency)
- 10 concurrent users: 4.2 queries/second aggregate throughput
- Error rate: 15/1000 queries (1.5%)

Errors primarily resulted from external API timeouts (60%), rate limiting (33%), and occasional parsing issues (7%). The system remained stable under moderate concurrent load.

### Parameter Sensitivity

We evaluated sensitivity to key configuration parameters:

**Similarity Threshold**:

| Threshold | Precision | Coverage | Hallucination Rate |
|-----------|-----------|----------|--------------------|
| 0.15 | 68% | 99% | 9% |
| 0.22 | 76.5% | 96% | 5% |
| 0.30 | 84% | 87% | 3% |

Higher thresholds improve precision and reduce hallucinations but decrease coverage. The selected threshold (0.22) balances these trade-offs.

**Context Chunks (N)**:

| N | Relevance | Hallucination | Mean Latency |
|---|-----------|---------------|--------------|
| 1 | 85% | 4% | 1.8 s |
| 3 | 93% | 5% | 2.4 s |
| 5 | 94% | 5% | 3.2 s |

N=3 provides optimal balance of response quality and latency.

---

## Discussion

### Principal Findings

This study designed, implemented, and evaluated a complete Retrieval-Augmented Generation-based Clinical Decision Support System addressing key limitations of direct language model deployment in healthcare. Principal findings include:

1. **Technical Feasibility**: The modular architecture successfully integrated presentation, application, and data layers to provide natural language clinical information access with transparent source attribution

2. **Responsive Performance**: Sub-second semantic retrieval (mean 287ms) and acceptable end-to-end latency (mean 2.4s) enable interactive clinical use

3. **Response Quality**: High relevance rate (93%), complete source citation (100%), and reduced hallucination rate (5% vs. reported baseline 10-30%) demonstrate effective retrieval-based grounding

4. **Conversational Capability**: Automated query reformulation improved multi-turn retrieval accuracy by 17 percentage points

5. **Modular Design**: Multi-provider support and clear component boundaries enable institutional adaptation based on deployment constraints

### Interpretation in Context of Existing Literature

Our findings align with and extend existing RAG research in healthcare:

**Comparison to Medical RAG Systems**: Our hallucination rate (5%) is comparable to MedRAG's reported 4-7% on medical QA benchmarks [16]. Our response relevance (93%) aligns with BiomedRAG's reported performance on literature tasks [17]. However, direct quantitative comparison is limited by dataset differences.

**Beyond Task-Specific Prototypes**: Unlike many existing implementations focusing on specific tasks (question answering, literature summarization), our architecture provides general-purpose clinical information access with patient context integration.

**System-Level Focus**: While much research emphasizes algorithmic improvements, we prioritize comprehensive system integration, deployment considerations, and practical performance characteristics relevant to institutional adoption.

### Strengths and Limitations

**Strengths**:

1. **Comprehensive Architecture**: Complete system design with documented components, interfaces, and integration patterns
2. **Multiple Safety Mechanisms**: Similarity gating, mandatory attribution, confidence scoring, disclaimer injection, and privacy protection
3. **Multi-Provider Flexibility**: Abstraction enabling institutional choice aligned with data governance requirements
4. **Transparent Evaluation**: Comprehensive reporting of performance metrics, limitations, and evaluation methodology
5. **Reproducible Implementation**: Open-source technology stack with detailed documentation

**Limitations**:

1. **Moderate Scale**: Knowledge base size (14,782 chunks) is smaller than production systems might require; scalability to 100,000+ chunks requires validation

2. **Constructed Queries**: Test queries were researcher-constructed rather than collected from authentic clinical use; real-world query distributions may differ

3. **Single Evaluator**: Relevance judgments by single expert introduce subjectivity; inter-annotator agreement measurement represents future work

4. **Lack of Clinical Outcome Measurement**: This study evaluated system performance, not clinical decision-making quality or patient outcomes—a critical limitation

5. **Single Configuration**: Evaluation used one embedding model and one language model; performance characteristics may vary with alternative providers

6. **Absence of Bias Evaluation**: We did not systematically evaluate performance across patient demographics, medical conditions, or demographic groups—an important ethical consideration

7. **No Long-Term Monitoring**: Evaluation represents a point-in-time assessment; longitudinal performance monitoring has not been conducted

### Ethical Considerations

**Decision Support, Not Decision-Making**:

This system is designed to **assist** healthcare professionals—not replace clinical judgment. All system outputs require verification  and interpretation by qualified clinicians. The system explicitly disclaims authority for medical advice, diagnosis, or treatment recommendations.

**This Is Not a Clinical Trial**:

We emphasize that this study evaluated system architecture and technical performance—we did not conduct a clinical trial or validation study. We made no measurements of:

- Clinical decision-making quality
- Diagnostic accuracy
- Treatment appropriateness
- Patient outcomes
- Workflow efficiency in real clinical settings

Such measurements are **essential prerequisites for clinical deployment** and represent critical future work.

**Data Privacy**:

The evaluation used publicly available medical guidelines and constructed queries—no patient data was collected or processed. However, real-world deployment would require strict compliance with healthcare data protection regulations (HIPAA, GDPR, etc.), encryption, access controls, and audit logging.

**Transparency and Explainability**:

While source citations enhance transparency, the internal reasoning process of neural language models remains opaque. Clinicians must understand that:

- Responses represent pattern-based generation informed by retrieved content
- The system does not perform explicit logical reasoning
- Citation indicates information source but not reasoning process

**Bias and Fairness**:

Medical knowledge bases may reflect biases present in source materials, potentially affecting information quality across patient populations. We did not implement explicit bias detection or mitigation mechanisms—a significant area for future work. Healthcare institutions must evaluate fairness across demographics before deployment.

**Accountability**:

While the system provides audit logging, healthcare institutions must establish clear accountability structures defining:

- Responsibility for system outputs
- Procedures for handling errors
- Mechanisms for incident reporting
- Oversight and governance processes

**Pre-Deployment Requirements**:

Before deployment in patient care settings, institutions must:

1. Conduct clinical validation studies assessing impact on decision-making and patient outcomes
2. Obtain appropriate regulatory clearances (e.g., FDA 510(k) if classified as medical device software)
3. Perform comprehensive integration testing with existing clinical information systems
4. Provide thorough user training on capabilities and limitations
5. Establish continuous monitoring and quality assessment procedures
6. Develop incident response protocols
7. Ensure compliance with all applicable healthcare regulations

### Implications for Practice and Policy

**For Healthcare Institutions**:

The reference architecture provides a starting point for institutions exploring AI-augmented clinical decision support. Key considerations include:

- Alignment with data governance requirements (on-premise vs. cloud deployment)
- Integration with existing clinical information systems
- User training and change management
- Continuous quality monitoring

**For Policymakers and Regulators**:

The transparency mechanisms (source citation, confidence scoring) and safety features (disclaimers, fallback responses) demonstrate approaches for responsible healthcare AI. However, standardized evaluation frameworks and regulatory guidance for clinical RAG systems remain limited.

**For Researchers**:

The evaluation methodology and identified limitations suggest research priorities including standardized benchmark datasets, bias mitigation strategies, explainability enhancements, and clinical validation study designs.

### Future Directions

**Clinical Validation**:

The most critical future work is clinical validation studies evaluating:

- Impact on clinical decision-making quality
- Workflow efficiency and clinician satisfaction
- Error rates and safety incidents
- Patient outcomes (in carefully controlled research settings)

**Technical Enhancements**:

- Multi-hop reasoning for complex queries requiring synthesis across sources
- Temporal reasoning prioritizing current guidelines
- Domain-specific embedding fine-tuning on medical corpora
- Post-generation fact verification mechanisms
- Multi-modal support incorporating medical imaging

**Ethical and Safety Improvements**:

- Bias detection and mitigation across demographics and conditions
- Enhanced explainability providing reasoning traces
- Adversarial robustness testing
- Fairness audits ensuring equitable performance

**Scale and Integration**:

- Validation at production scale (100,000+ documents)
- Integration with Electronic Health Record systems via HL7 PHIR
- Federated knowledge bases enabling multi-institutional collaboration
- Real-time knowledge updates synchronized with guideline publications

**Standardization**:

- Development of benchmark datasets for clinical RAG evaluation
- Standardized evaluation protocols and metrics
- Best practices guidance for responsible deployment

---

## Conclusions

This study presented a comprehensive Retrieval-Augmented Generation-based Clinical Decision Support System addressing key limitations of direct language model deployment in healthcare through external knowledge grounding, transparent source attribution, and systematic safety mechanisms.

The modular three-tier architecture successfully integrated web presentation, microservices orchestration, and vector database retrieval. System-level evaluation demonstrated responsive performance (sub-second retrieval, 2.4-second mean end-to-end latency), high response quality (93% relevance, 100% citation rate), and reduced hallucination (5%) compared to baseline language models.

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
