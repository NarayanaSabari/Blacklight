# Resume Tailor Integration - Implementation Plan

## Overview

This document outlines the phased implementation plan for integrating the Resume Tailor feature into Blacklight Portal. The plan is designed for incremental delivery with working functionality at each phase.

---

## Phase Summary

| Phase | Name | Duration | Deliverables |
|-------|------|----------|--------------|
| 1 | Foundation | 2-3 days | Database models, AI service setup, basic backend |
| 2 | Core Tailoring | 3-4 days | Tailoring service, Inngest jobs, scoring |
| 3 | API Layer | 2 days | REST endpoints, SSE streaming |
| 4 | Frontend MVP | 3-4 days | Basic UI, progress display, results view |
| 5 | Polish & Features | 2-3 days | Export, bulk operations, UX improvements |

**Total Estimated Time: 12-16 days**

---

## Phase 1: Foundation (Days 1-3)

### Goals
- Set up database models
- Configure AI providers
- Create basic service structure

### Tasks

#### 1.1 Database Models
```
[ ] Create TailoredResume model
    File: server/app/models/tailored_resume.py
    
[ ] Create migration script
    Command: python manage.py create-migration "add_tailored_resumes"
    
[ ] Run migration
    Command: python manage.py migrate
    
[ ] Register model in __init__.py
    File: server/app/models/__init__.py
```

#### 1.2 AI Service Setup (Reusing Existing)
```
[ ] Verify existing AI services work
    - EmbeddingService (server/app/services/embedding_service.py)
    - Uses google.generativeai for Gemini
    - Uses models/embedding-001 for 768-dim embeddings
    
[ ] Create LLM wrapper service for resume tailoring
    File: server/app/services/resume_tailor/llm_service.py
    - Wraps existing genai.GenerativeModel pattern
    - Uses gemini-2.5-flash (from settings.gemini_model)
    
[ ] No new providers needed - use existing GOOGLE_API_KEY
    Already configured in: config/settings.py
    - ai_parsing_provider = "gemini"
    - google_api_key
    - gemini_model = "gemini-2.5-flash"
    - gemini_embedding_model = "models/embedding-001"
```

#### 1.3 Pydantic Schemas
```
[ ] Create tailored resume schemas
    File: server/app/schemas/tailored_resume.py
    - TailoredResumeCreate
    - TailoredResumeResponse
    - TailorOptions
    - ProgressUpdate
```

#### 1.4 Basic Service Structure
```
[ ] Create resume tailor service module
    Directory: server/app/services/resume_tailor/
    File: server/app/services/resume_tailor/__init__.py
    File: server/app/services/resume_tailor/tailor_service.py (skeleton)
```

### Deliverables
- ✅ Database table created and migrated
- ✅ LLM wrapper service created (reusing existing Gemini setup)
- ✅ Basic Python package structure

### Testing
```bash
# Verify migration
python manage.py migrate

# Verify model import
python -c "from app.models import TailoredResume; print('OK')"

# Verify existing AI services work
python -c "from app.services.embedding_service import EmbeddingService; print('OK')"
```

---

## Phase 2: Core Tailoring Logic (Days 4-7)

### Goals
- Implement resume parsing
- Implement keyword extraction
- Implement scoring logic
- Implement LLM improvement

### Tasks

#### 2.1 Resume Parser Service
```
[ ] Create parser service (adapted from Resume-Matcher)
    File: server/app/services/resume_tailor/parser_service.py
    
    Functions:
    - parse_resume_to_markdown(content: bytes) -> str
    - parse_job_description(text: str) -> dict
    - extract_structured_data(markdown: str) -> dict
```

#### 2.2 Keyword Extraction Service
```
[ ] Create keyword service
    File: server/app/services/resume_tailor/keyword_service.py
    
    Functions:
    - extract_keywords(text: str) -> List[str]
    - compare_keywords(resume_kw, job_kw) -> dict
    - prioritize_skills(job_keywords, resume_keywords) -> List[str]
```

#### 2.3 Scoring Service
```
[ ] Create scoring service
    File: server/app/services/resume_tailor/scoring_service.py
    
    Functions:
    - calculate_cosine_similarity(vec1, vec2) -> float
    - calculate_keyword_overlap(resume_kw, job_kw) -> float
    - calculate_combined_score(semantic, keyword) -> float
```

#### 2.4 Improvement Service (Core Logic)
```
[ ] Create improvement service (adapted from Resume-Matcher)
    File: server/app/services/resume_tailor/improvement_service.py
    
    Functions:
    - improve_resume(resume_md, job_desc, options) -> dict
    - run_improvement_iteration(resume, job, target_score) -> str
    - track_improvements(original, improved) -> List[dict]
```

#### 2.5 Prompts
```
[ ] Create prompt templates
    File: server/app/services/resume_tailor/prompts/__init__.py
    File: server/app/services/resume_tailor/prompts/improvement.py
    File: server/app/services/resume_tailor/prompts/extraction.py
```

#### 2.6 Main Tailor Service
```
[ ] Complete tailor service implementation
    File: server/app/services/resume_tailor/tailor_service.py
    
    Methods:
    - analyze(candidate_id, job_id) -> AnalysisResult
    - tailor(candidate_id, job_id, options) -> TailoredResume
    - get_progress(tailor_id) -> ProgressUpdate
```

### Deliverables
- ✅ Resume parsing working
- ✅ Keyword extraction working
- ✅ Score calculation working
- ✅ LLM improvement working

### Testing
```python
# test_resume_tailor_service.py
def test_parse_resume():
    ...

def test_extract_keywords():
    ...

def test_calculate_score():
    ...

def test_improve_resume():
    ...
```

---

## Phase 3: API & Inngest (Days 8-9)

### Goals
- Create REST API endpoints
- Implement SSE streaming
- Set up Inngest background jobs

### Tasks

#### 3.1 REST API Routes
```
[ ] Create resume tailor routes
    File: server/app/routes/resume_tailor_routes.py
    
    Endpoints:
    - POST /api/resume-tailor/analyze
    - GET  /api/resume-tailor/analyze/{analysis_id}
    - POST /api/resume-tailor/tailor
    - GET  /api/resume-tailor/tailor/{tailor_id}
    - GET  /api/resume-tailor/tailor/{tailor_id}/stream
    - GET  /api/candidates/{id}/tailored-resumes
    - GET  /api/resume-tailor/{tailor_id}/export
    - POST /api/resume-tailor/{tailor_id}/apply
    
[ ] Register blueprint
    File: server/app/__init__.py (in register_blueprints)
```

#### 3.2 SSE Streaming Implementation
```
[ ] Implement SSE endpoint for progress streaming
    File: server/app/routes/resume_tailor_routes.py
    
    Using Flask's Response with generator:
    - stream_progress(tailor_id) generator
    - Redis pub/sub for real-time updates
```

#### 3.3 Inngest Background Jobs
```
[ ] Create Inngest functions
    File: server/app/inngest/functions/resume_tailor.py
    
    Functions:
    - resume_tailor_analyze: Event "resume-tailor/analyze"
    - resume_tailor_generate: Event "resume-tailor/generate"
    
[ ] Register functions
    File: server/app/inngest/__init__.py
```

#### 3.4 Add Permissions
```
[ ] Add resume tailor permissions to RBAC
    File: server/app/seeds/permissions.py
    
    New permissions:
    - resume_tailor.view
    - resume_tailor.create
    - resume_tailor.export
    - resume_tailor.apply
```

### Deliverables
- ✅ All API endpoints working
- ✅ SSE streaming working
- ✅ Background jobs processing

### Testing
```bash
# Test analyze endpoint
curl -X POST http://localhost:5000/api/resume-tailor/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": 1, "job_posting_id": 1}'

# Test streaming
curl -N http://localhost:5000/api/resume-tailor/tailor/uuid/stream \
  -H "Authorization: Bearer $TOKEN"
```

---

## Phase 4: Frontend MVP (Days 10-13)

### Goals
- Create basic tailoring UI
- Show progress during processing
- Display results with comparison

### Tasks

#### 4.1 API Client
```
[ ] Create resume tailor API client
    File: ui/portal/src/api/resume-tailor.ts
```

#### 4.2 Context Provider
```
[ ] Create ResumeTailorContext
    File: ui/portal/src/context/ResumeTailorContext.tsx
```

#### 4.3 Core Components
```
[ ] Create JobSelectorDialog
    File: ui/portal/src/components/resume-tailor/JobSelectorDialog.tsx

[ ] Create MatchScoreDisplay
    File: ui/portal/src/components/resume-tailor/MatchScoreDisplay.tsx

[ ] Create TailoringProgress
    File: ui/portal/src/components/resume-tailor/TailoringProgress.tsx

[ ] Create ResumePreview
    File: ui/portal/src/components/resume-tailor/ResumePreview.tsx

[ ] Create ImprovementsList
    File: ui/portal/src/components/resume-tailor/ImprovementsList.tsx

[ ] Create SkillGapAnalysis
    File: ui/portal/src/components/resume-tailor/SkillGapAnalysis.tsx
```

#### 4.4 Main Page
```
[ ] Create ResumeTailorPage
    File: ui/portal/src/pages/candidates/ResumeTailorPage.tsx
    
[ ] Add route
    File: ui/portal/src/routes.tsx
    Route: /candidates/:candidateId/tailor/:jobId
```

#### 4.5 Integration Points
```
[ ] Add "Tailor Resume" button to CandidateDetailPage
    File: ui/portal/src/pages/candidates/CandidateDetailPage.tsx

[ ] Add "Tailor for this Job" action to match cards
    File: ui/portal/src/components/matches/MatchCard.tsx
```

### Deliverables
- ✅ Users can initiate resume tailoring
- ✅ Progress displayed during processing
- ✅ Results shown with before/after comparison
- ✅ Improvements listed

### Testing
- Manual testing through UI
- Verify SSE connection works
- Test with different resume/job combinations

---

## Phase 5: Polish & Features (Days 14-16)

### Goals
- Add export functionality
- Add bulk tailoring
- Improve UX

### Tasks

#### 5.1 Export Service
```
[ ] Create export service
    File: server/app/services/resume_tailor/export_service.py
    
    Methods:
    - export_to_pdf(tailored_resume) -> bytes
    - export_to_docx(tailored_resume) -> bytes
    - export_to_markdown(tailored_resume) -> str
    
[ ] Add dependencies
    File: server/requirements.txt
    - weasyprint (for PDF)
    - python-docx (for DOCX)
```

#### 5.2 Export UI
```
[ ] Create ExportOptionsMenu
    File: ui/portal/src/components/resume-tailor/ExportOptionsMenu.tsx
```

#### 5.3 Tailored Resumes History
```
[ ] Create TailoredResumesTab for candidate detail
    File: ui/portal/src/components/candidates/TailoredResumesTab.tsx
    
[ ] Add tab to CandidateDetailPage
```

#### 5.4 Apply Tailored Resume
```
[ ] Create apply confirmation dialog
    File: ui/portal/src/components/resume-tailor/ApplyResumeDialog.tsx
    
[ ] Implement apply logic in backend
```

#### 5.5 Bulk Operations (Optional)
```
[ ] Add bulk tailor endpoint
    POST /api/resume-tailor/bulk

[ ] Add bulk tailor UI in job detail page
```

#### 5.6 UX Improvements
```
[ ] Add loading states
[ ] Add error handling
[ ] Add success toasts
[ ] Add keyboard shortcuts
[ ] Add mobile responsiveness
```

### Deliverables
- ✅ Export to PDF/DOCX working
- ✅ History of tailored resumes
- ✅ Apply to candidate profile
- ✅ Polished user experience

---

## File Structure Summary

### Backend
```
server/app/
├── models/
│   └── tailored_resume.py          # NEW
├── schemas/
│   └── tailored_resume.py          # NEW
├── routes/
│   └── resume_tailor_routes.py     # NEW
├── services/
│   ├── embedding_service.py        # EXISTING - Reuse for embeddings
│   ├── ai_role_normalization_service.py  # EXISTING - Pattern reference
│   ├── role_suggestion_service.py  # EXISTING - Pattern reference
│   └── resume_tailor/              # NEW
│       ├── __init__.py
│       ├── tailor_service.py       # Main orchestration
│       ├── llm_service.py          # Wraps Gemini for LLM calls
│       ├── parser_service.py
│       ├── keyword_service.py
│       ├── scoring_service.py
│       ├── improvement_service.py
│       ├── export_service.py
│       └── prompts/
│           ├── __init__.py
│           ├── improvement.py
│           └── extraction.py
└── inngest/
    └── functions/
        └── resume_tailor.py        # NEW
```

### Frontend
```
ui/portal/src/
├── api/
│   └── resume-tailor.ts            # NEW
├── context/
│   └── ResumeTailorContext.tsx     # NEW
├── pages/
│   └── candidates/
│       └── ResumeTailorPage.tsx    # NEW
└── components/
    └── resume-tailor/              # NEW
        ├── JobSelectorDialog.tsx
        ├── ResumeTailorCard.tsx
        ├── MatchScoreDisplay.tsx
        ├── SkillGapAnalysis.tsx
        ├── ImprovementsList.tsx
        ├── ResumePreview.tsx
        ├── ResumeDiffView.tsx
        ├── TailoringProgress.tsx
        ├── ExportOptionsMenu.tsx
        └── ApplyResumeDialog.tsx
```

---

## Dependencies to Add

### Backend (requirements.txt)
```
# PDF generation
weasyprint>=60.0

# DOCX generation
python-docx>=1.0.0

# Markdown processing
markdown>=3.5

# Already installed - google-generativeai is used for Gemini
# No new AI dependencies needed
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "marked": "^12.0.0",
    "diff": "^5.2.0"
  }
}
```

---

## Environment Variables

```bash
# EXISTING - Already configured, no changes needed
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001
GEMINI_EMBEDDING_DIMENSION=768

# NEW (Optional) - Resume Tailor specific tuning
RESUME_TAILOR_MAX_ITERATIONS=5           # Max LLM improvement attempts
RESUME_TAILOR_TARGET_SCORE=0.85          # Stop when this score reached
RESUME_TAILOR_TIMEOUT_SECONDS=300        # Max processing time
RESUME_TAILOR_MAX_BULK_SIZE=50           # Max candidates in bulk operation
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini API rate limits | High | Implement retry logic with exponential backoff |
| Long processing times | Medium | Show progress via SSE, allow cancellation |
| Inaccurate improvements | Medium | Keep original, require user review before apply |
| PDF export issues | Low | Fall back to DOCX/Markdown |
| SSE connection drops | Medium | Auto-reconnect, polling fallback |

---

## Success Criteria

### Functional
- [ ] Can tailor a resume for a specific job
- [ ] Shows progress during tailoring
- [ ] Displays before/after comparison
- [ ] Exports to PDF and DOCX
- [ ] Lists tailored resume history

### Performance
- [ ] Tailoring completes in < 60 seconds
- [ ] UI updates in real-time via SSE
- [ ] Export generates in < 5 seconds

### Quality
- [ ] Score improvement of 10-25% on average
- [ ] No fabricated information added
- [ ] Original resume structure preserved

---

## Next Steps After Approval

1. **Review this plan** and provide feedback
2. **Confirm AI provider** preference (Gemini vs OpenAI vs Ollama)
3. **Approve phase sequence** or request reordering
4. **Begin Phase 1** implementation

---

**Document Status**: Draft - Pending Approval  
**Last Updated**: 2025-12-14  
**Estimated Start**: Upon approval  
**Estimated Completion**: 12-16 days from start
