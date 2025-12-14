# Resume Tailor Integration - Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BLACKLIGHT PORTAL (React)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │ CandidateDetail │  │ CandidateMatches│  │    ResumeTailorPage         │ │
│  │     Page        │  │     Page        │  │                             │ │
│  │                 │  │                 │  │  ┌─────────────────────────┐│ │
│  │ [Tailor Resume] │  │ [Tailor for Job]│  │  │ JobSelector             ││ │
│  │     Button      │  │    Actions      │  │  │ OriginalResumePreview   ││ │
│  └────────┬────────┘  └────────┬────────┘  │  │ TailoredResumePreview   ││ │
│           │                    │           │  │ MatchScoreComparison    ││ │
│           └────────────────────┴───────────│  │ SkillGapAnalysis        ││ │
│                                            │  │ ImprovementSuggestions  ││ │
│                                            │  │ ExportActions           ││ │
│                                            │  └─────────────────────────┘│ │
│                                            └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BLACKLIGHT BACKEND (Flask)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    API Routes Layer                                   │  │
│  │  /api/resume-tailor/                                                  │  │
│  │    POST /analyze           - Start analysis (returns job_id)         │  │
│  │    GET  /analyze/:id       - Get analysis status/result              │  │
│  │    POST /tailor            - Start tailoring (returns job_id)        │  │
│  │    GET  /tailor/:id        - Get tailoring status/result (SSE)       │  │
│  │    GET  /candidates/:id/tailored-resumes - List tailored versions    │  │
│  │    POST /export            - Export to PDF/DOCX                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                                      │  │
│  │                                                                       │  │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────────┐ │  │
│  │  │ ResumeTailorService│  │ ResumeParserService│  │  GeminiService  │ │  │
│  │  │                    │  │                    │  │  (EXISTING)     │ │  │
│  │  │ - analyze()        │  │ - parse_resume()   │  │                 │ │  │
│  │  │ - tailor()         │  │ - parse_job()      │  │ - genai.        │ │  │
│  │  │ - compare()        │  │ - extract_keywords()│ │   GenerativeModel│ │  │
│  │  │ - get_suggestions()│  │                    │  │ - gemini-2.5-   │ │  │
│  │  └────────────────────┘  └────────────────────┘  │   flash         │ │  │
│  │                                                  └─────────────────┘ │  │
│  │  ┌────────────────────┐  ┌────────────────────┐                      │  │
│  │  │ EmbeddingService   │  │ ExportService      │                      │  │
│  │  │  (EXISTING)        │  │  (NEW)             │                      │  │
│  │  │ - generate_embedding│ │ - to_pdf()         │                      │  │
│  │  │ - models/embedding │  │ - to_docx()        │                      │  │
│  │  │   -001 (768 dim)   │  │                    │                      │  │
│  │  └────────────────────┘  └────────────────────┘                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Inngest Background Jobs                            │  │
│  │                                                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ resume-tailor/analyze                                          │  │  │
│  │  │   - Parse resume content                                        │  │  │
│  │  │   - Parse job description                                       │  │  │
│  │  │   - Extract keywords from both                                  │  │  │
│  │  │   - Calculate initial match score                               │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ resume-tailor/generate                                         │  │  │
│  │  │   - Generate ATS recommendations                                │  │  │
│  │  │   - Build skill priority list                                   │  │  │
│  │  │   - Improve resume with LLM (up to 5 iterations)               │  │  │
│  │  │   - Calculate new match score                                   │  │  │
│  │  │   - Store tailored resume                                       │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Data Layer (PostgreSQL)                            │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │   candidates    │  │  job_postings   │  │ tailored_resumes    │   │  │
│  │  │                 │  │                 │  │ (NEW)               │   │  │
│  │  │ - resume content│  │ - description   │  │                     │   │  │
│  │  │ - parsed_data   │  │ - skills        │  │ - candidate_id      │   │  │
│  │  │ - embedding     │  │ - embedding     │  │ - job_posting_id    │   │  │
│  │  └─────────────────┘  └─────────────────┘  │ - original_content  │   │  │
│  │                                            │ - tailored_content  │   │  │
│  │                                            │ - original_score    │   │  │
│  │                                            │ - tailored_score    │   │  │
│  │                                            │ - improvements      │   │  │
│  │                                            │ - skill_comparison  │   │  │
│  │                                            └─────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Components (ui/portal)

#### New Pages:
- **ResumeTailorPage** (`/candidates/:id/tailor/:jobId`)
  - Main page for resume tailoring workflow
  - Split-screen view: Original | Tailored
  - Match score progress indicator
  - Improvement suggestions panel

#### New Components:
```
src/components/resume-tailor/
├── JobSelectorDialog.tsx       # Modal to select job for tailoring
├── ResumeTailorCard.tsx        # Card showing tailored resume summary
├── MatchScoreDisplay.tsx       # Visual score comparison (before/after)
├── SkillGapAnalysis.tsx        # Table of matched/missing skills
├── ImprovementsList.tsx        # List of suggested improvements
├── ResumePreview.tsx           # Markdown/HTML resume preview
├── ResumeDiffView.tsx          # Side-by-side diff visualization
├── TailoringProgress.tsx       # SSE-based progress indicator
└── ExportOptionsMenu.tsx       # Export to PDF/DOCX dropdown
```

#### Modified Pages:
- **CandidateDetailPage**: Add "Tailor Resume" action button
- **CandidateMatchesPage**: Add "Tailor for this Job" action per match
- **JobDetailPage**: Add "Tailor Candidates" bulk action

### 2. Backend Services (server/app)

#### New Services:
```
server/app/services/
├── resume_tailor/
│   ├── __init__.py
│   ├── tailor_service.py       # Main orchestration service
│   ├── parser_service.py       # Resume/Job parsing (adapted from RM)
│   ├── keyword_service.py      # Keyword extraction (adapted from RM)
│   ├── improvement_service.py  # Resume improvement (adapted from RM)
│   └── export_service.py       # PDF/DOCX generation
```

#### AI Services (Reusing Existing):
```
server/app/services/
├── embedding_service.py        # EXISTING - Uses Gemini models/embedding-001 (768-dim)
├── ai_role_normalization_service.py  # EXISTING - Pattern for using Gemini
├── role_suggestion_service.py  # EXISTING - Pattern for LangChain + Gemini
└── resume_tailor/
    └── llm_service.py          # NEW - Wraps Gemini for resume improvement
```

**Existing AI Configuration (config/settings.py):**
```python
# Already configured - no new providers needed
ai_parsing_provider: str = "gemini"  # AI_PARSING_PROVIDER
google_api_key: str              # GOOGLE_API_KEY
gemini_model: str = "gemini-2.5-flash"  # GEMINI_MODEL
gemini_embedding_model: str = "models/embedding-001"  # GEMINI_EMBEDDING_MODEL
gemini_embedding_dimension: int = 768  # GEMINI_EMBEDDING_DIMENSION
```

### 3. New API Endpoints

```python
# server/app/routes/resume_tailor_routes.py

POST /api/resume-tailor/analyze
# Start analysis job
# Body: { candidate_id, job_posting_id }
# Returns: { analysis_id, status: "processing" }

GET /api/resume-tailor/analyze/{analysis_id}
# Get analysis result
# Returns: { status, match_score, keywords, skill_gap }

POST /api/resume-tailor/tailor
# Start tailoring job  
# Body: { candidate_id, job_posting_id, options? }
# Returns: { tailor_id, status: "processing" }

GET /api/resume-tailor/tailor/{tailor_id}
# Get tailoring result (supports SSE streaming)
# Returns: { status, tailored_resume, improvements, scores }

GET /api/candidates/{candidate_id}/tailored-resumes
# List all tailored versions for a candidate
# Returns: { tailored_resumes: [...] }

GET /api/resume-tailor/{tailor_id}/export
# Export tailored resume
# Query: ?format=pdf|docx
# Returns: File download

POST /api/resume-tailor/{tailor_id}/apply
# Apply tailored resume to candidate record
# Returns: { success: true }
```

### 4. New Database Model

```python
# server/app/models/tailored_resume.py

class TailoredResume(BaseModel):
    """Stores tailored resume versions"""
    __tablename__ = 'tailored_resumes'
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    job_posting_id = Column(Integer, ForeignKey('job_postings.id'), nullable=False)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey('portal_users.id'), nullable=False)
    
    # Original Content
    original_resume_content = Column(Text, nullable=False)  # Markdown
    original_resume_keywords = Column(ARRAY(String))
    
    # Tailored Content
    tailored_resume_content = Column(Text, nullable=False)  # Markdown
    tailored_resume_html = Column(Text)  # Rendered HTML
    tailored_resume_keywords = Column(ARRAY(String))
    
    # Scoring
    original_match_score = Column(DECIMAL(5, 4))  # 0.0000 to 1.0000
    tailored_match_score = Column(DECIMAL(5, 4))
    score_improvement = Column(DECIMAL(5, 4))  # Difference
    
    # Analysis Results (JSONB)
    skill_comparison = Column(JSONB)
    # [{ skill, resume_mentions, job_mentions }]
    
    improvements = Column(JSONB)
    # [{ section, suggestion, line_number }]
    
    job_keywords = Column(ARRAY(String))
    matched_skills = Column(ARRAY(String))
    missing_skills = Column(ARRAY(String))
    
    # Metadata
    processing_status = Column(String(50))  # pending, processing, completed, failed
    processing_error = Column(Text)
    ai_provider = Column(String(50))  # openai, ollama, gemini
    ai_model = Column(String(100))
    processing_duration_seconds = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship('Candidate', backref='tailored_resumes')
    job_posting = relationship('JobPosting', backref='tailored_resumes')
    tenant = relationship('Tenant')
    created_by = relationship('PortalUser')
```

### 5. Inngest Functions

```python
# server/app/inngest/functions/resume_tailor.py

@inngest_client.create_function(
    fn_id="resume-tailor-analyze",
    trigger=inngest.TriggerEvent(event="resume-tailor/analyze")
)
async def analyze_resume_job(ctx, step):
    """Analyze resume against job description"""
    # Step 1: Parse resume
    # Step 2: Parse job description
    # Step 3: Extract keywords
    # Step 4: Calculate match score
    # Step 5: Identify skill gaps
    pass

@inngest_client.create_function(
    fn_id="resume-tailor-generate",
    trigger=inngest.TriggerEvent(event="resume-tailor/generate")
)
async def generate_tailored_resume(ctx, step):
    """Generate tailored resume with improvements"""
    # Step 1: Build ATS recommendations
    # Step 2: Build skill priority text
    # Step 3: Improve resume (iterative LLM calls)
    # Step 4: Calculate new score
    # Step 5: Generate analysis
    # Step 6: Store result
    pass
```

## Data Flow

### Tailoring Workflow:

```
1. User clicks "Tailor Resume" for candidate + job
                    │
                    ▼
2. Frontend calls POST /api/resume-tailor/tailor
                    │
                    ▼
3. Backend creates TailoredResume record (status: pending)
   Triggers Inngest event "resume-tailor/generate"
   Returns tailor_id
                    │
                    ▼
4. Frontend opens SSE connection to GET /api/resume-tailor/tailor/{id}
                    │
                    ▼
5. Inngest function processes:
   ├─ Parse resume & job
   ├─ Extract keywords → SSE: { status: "extracting_keywords" }
   ├─ Calculate initial score → SSE: { status: "scoring", score: 0.72 }
   ├─ Generate improvements → SSE: { status: "improving" }
   ├─ Calculate final score → SSE: { status: "completed", score: 0.89 }
   └─ Update TailoredResume record
                    │
                    ▼
6. Frontend receives completion, fetches full result
                    │
                    ▼
7. User reviews tailored resume, can export or apply
```

## Configuration

### Environment Variables:

**No new AI configuration needed!** Resume Tailor uses existing Gemini setup:

```bash
# EXISTING - Already in .env (no changes needed)
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001
GEMINI_EMBEDDING_DIMENSION=768

# NEW - Resume Tailor specific settings (optional)
RESUME_TAILOR_MAX_ITERATIONS=5        # Max LLM improvement iterations
RESUME_TAILOR_TARGET_SCORE=0.85       # Stop when this score is reached
RESUME_TAILOR_TIMEOUT_SECONDS=300     # Max processing time
```

## Integration with Existing Blacklight Components

### Reusing Existing:
1. **Candidate Model**: Use existing `parsed_resume_data` and `embedding`
2. **JobPosting Model**: Use existing `description`, `skills`, `embedding`
3. **CandidateJobMatch Model**: Link tailored resumes to matches
4. **Inngest**: Use existing Inngest client setup
5. **Auth Middleware**: Use existing `@require_portal_auth`

### Adapting from Resume-Matcher:
1. **LLM Calls**: Use existing `google.generativeai.GenerativeModel` pattern (see `ai_role_normalization_service.py`)
2. **Structured Output**: Use existing `langchain_google_genai.ChatGoogleGenerativeAI` pattern (see `role_suggestion_service.py`)
3. **Embeddings**: Use existing `EmbeddingService.generate_embedding()` (768-dim Gemini embeddings)
4. **Prompts**: Keep Resume-Matcher prompts with minor adjustments
5. **Scoring Logic**: Directly port cosine similarity logic (already exists in `job_matching_service.py`)

---

**Document Status**: Draft - Pending Approval  
**Last Updated**: 2025-12-14  
