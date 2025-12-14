# Resume Tailor Integration - Overview

## Executive Summary

This document outlines the integration plan for adding **Resume Tailoring** functionality to the Blacklight HR Portal. The feature will allow recruiters and managers to automatically tailor a candidate's resume to match a specific job description, improving the candidate's chances of passing ATS (Applicant Tracking System) screening.

## What is Resume Tailoring?

Resume Tailoring is an AI-powered feature that:
1. **Analyzes** a candidate's existing resume and extracts structured data
2. **Compares** the resume against a specific job description
3. **Identifies gaps** in keywords, skills, and experience presentation
4. **Generates** an optimized version of the resume that better matches the job
5. **Provides** improvement suggestions and match scoring

## Source: Resume-Matcher Open Source Project

We will integrate core components from the [Resume-Matcher](https://github.com/srbhr/Resume-Matcher) open-source project:

### Core Capabilities from Resume-Matcher:
- **Resume Parsing**: Converts PDF/DOCX to structured data (personal info, experience, skills, education)
- **Job Description Parsing**: Extracts requirements, keywords, and qualifications
- **Keyword Extraction**: Uses LLM to extract relevant keywords from both documents
- **Embedding-based Scoring**: Cosine similarity using vector embeddings
- **Resume Improvement**: LLM-powered resume rewriting to increase match score
- **ATS Recommendations**: Specific suggestions for improving ATS compatibility

### AI Provider Support:
- **OpenAI** (GPT-4, GPT-3.5)
- **Ollama** (Local models like Llama, Mistral)
- **LlamaIndex** (Various providers)

## Integration Context

### Blacklight Current Architecture:
- **Backend**: Flask (Python 3.11.9) with SQLAlchemy
- **Frontend**: React + TypeScript + Vite (shadcn/ui + Tailwind)
- **Database**: PostgreSQL with pgvector for embeddings
- **Background Jobs**: Inngest
- **Multi-tenant**: Tenant-based data isolation

### Resume-Matcher Architecture:
- **Backend**: FastAPI (Python 3.12+) with async SQLAlchemy
- **Frontend**: Next.js 15+ (not relevant for integration)
- **Database**: SQLite (we'll adapt to PostgreSQL)
- **AI Agents**: Modular provider system (OpenAI/Ollama/LlamaIndex)

## Integration Approach

We will **NOT** run Resume-Matcher as a separate service. Instead, we will:

1. **Extract and adapt** the core Python services from Resume-Matcher
2. **Integrate** them into Blacklight's Flask backend as new services
3. **Create new API endpoints** in Blacklight for resume tailoring
4. **Build new UI components** in the Portal frontend
5. **Use Inngest** for background processing of AI operations

## Key User Stories

### Primary User: Recruiter/Manager
1. **View Candidate Matches**: See a candidate's matched jobs with scores
2. **Select Job for Tailoring**: Choose a specific job to tailor the resume for
3. **Initiate Tailoring**: Click "Tailor Resume" to start the AI process
4. **Review Results**: See the tailored resume with improvements highlighted
5. **Compare Versions**: Side-by-side view of original vs. tailored resume
6. **Download/Export**: Export the tailored resume as PDF/DOCX
7. **Apply Changes**: Optionally update the candidate's stored resume

### Secondary User: Team Lead
1. **Bulk Tailoring**: Tailor multiple candidates' resumes for the same job
2. **Review Queue**: Review tailored resumes before sending to clients

## Feature Scope

### Phase 1 (MVP)
- Single candidate resume tailoring for a single job
- Match score display (original vs. improved)
- Skill gap analysis
- Side-by-side resume comparison
- Markdown preview of tailored resume

### Phase 2 (Enhancement)
- PDF/DOCX export of tailored resume
- Bulk tailoring for multiple candidates
- Template-based resume formatting
- History of tailored versions

### Phase 3 (Advanced)
- Custom AI prompts per tenant
- Industry-specific keyword databases
- Integration with external ATS systems
- Auto-tailoring on job match creation

## Success Metrics

1. **Match Score Improvement**: Average increase in cosine similarity after tailoring
2. **Usage Adoption**: % of recruiters using the tailoring feature
3. **Time Savings**: Reduction in manual resume editing time
4. **Candidate Placement**: Correlation with successful placements

## Dependencies

### Required:
- OpenAI API key OR Ollama installation (for AI processing)
- Existing candidate resume in system
- Existing job posting in system

### Optional:
- PDF generation library (WeasyPrint or similar)
- DOCX generation library (python-docx)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| AI hallucination | Medium | Strict prompts to only use existing resume content |
| Processing time | Medium | Background processing with Inngest, progress indicators |
| API costs | Low | Caching, Ollama option for local processing |
| Data privacy | High | All processing in-system, no external storage |

## Next Steps

1. Review and approve this plan
2. Proceed to detailed architecture design (02-ARCHITECTURE.md)
3. Implement backend services
4. Build frontend components
5. Testing and QA
6. Staged rollout

---

**Document Status**: Draft - Pending Approval  
**Last Updated**: 2025-12-14  
**Author**: GitHub Copilot  
