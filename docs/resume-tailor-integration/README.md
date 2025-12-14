# Resume Tailor Integration - Documentation Index

## Overview

This documentation set outlines the complete integration plan for adding a Resume Tailor feature to Blacklight Portal. The feature allows HR staff and recruiters to automatically tailor candidate resumes to match specific job postings, improving ATS compatibility and match scores.

---

## Documents

| # | Document | Description |
|---|----------|-------------|
| 1 | [Overview](./01-OVERVIEW.md) | Executive summary, project context, integration points, key features, and success metrics |
| 2 | [Architecture](./02-ARCHITECTURE.md) | System architecture diagrams, component details, data flow, and configuration |
| 3 | [API Design](./03-API-DESIGN.md) | REST API endpoints, request/response formats, error handling, and rate limits |
| 4 | [Frontend](./04-FRONTEND.md) | React components, pages, context providers, and UI patterns |
| 5 | [Data Models](./05-DATA-MODELS.md) | Database schemas, migrations, Pydantic schemas, and entity relationships |
| 6 | [Implementation](./06-IMPLEMENTATION.md) | Phased rollout plan, tasks checklist, dependencies, and success criteria |

---

## Quick Reference

### Feature Summary

**Resume Tailor** enables:
- Analyzing candidate resumes against job descriptions
- Automatically improving resumes to match job requirements
- Side-by-side comparison of original vs tailored resumes
- Exporting tailored resumes to PDF/DOCX
- Tracking all tailored versions per candidate

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, TanStack Query, shadcn/ui |
| Backend | Flask, SQLAlchemy, Pydantic |
| Background Jobs | Inngest |
| AI/LLM | Google Gemini (`gemini-2.5-flash`) via `google-generativeai` |
| Embeddings | Google Gemini (`models/embedding-001`, 768-dim) |
| Database | PostgreSQL |
| Streaming | SSE (Server-Sent Events) |

### Key Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/resume-tailor/tailor` | Start tailoring job |
| GET | `/api/resume-tailor/tailor/{id}` | Get tailoring result |
| GET | `/api/resume-tailor/tailor/{id}/stream` | SSE progress stream |
| GET | `/api/resume-tailor/{id}/export` | Export to PDF/DOCX |

### New Database Table

```
tailored_resumes
├── candidate_id (FK)
├── job_posting_id (FK)
├── original_resume_content
├── tailored_resume_content
├── original_match_score
├── tailored_match_score
├── improvements (JSONB)
└── skill_comparison (JSONB)
```

### Estimated Timeline

| Phase | Duration |
|-------|----------|
| Foundation | 2-3 days |
| Core Tailoring | 3-4 days |
| API Layer | 2 days |
| Frontend MVP | 3-4 days |
| Polish & Features | 2-3 days |
| **Total** | **12-16 days** |

---

## Source Reference

This integration is inspired by the [Resume-Matcher](https://github.com/srbhr/Resume-Matcher) open-source project, adapting its core concepts for Blacklight's architecture:

| Resume-Matcher Feature | Blacklight Adaptation |
|------------------------|----------------------|
| FastAPI async services | Flask sync services + Inngest |
| SQLite database | PostgreSQL (existing) |
| OpenAI/Ollama | Gemini (existing) + OpenAI/Ollama options |
| MarkItDown parsing | Reuse existing resume parser |
| Cosine similarity | Port scoring logic |
| Next.js frontend | React with shadcn/ui |

---

## Approval Checklist

Before implementation begins, please confirm:

- [ ] Architecture approved (02-ARCHITECTURE.md)
- [ ] API design approved (03-API-DESIGN.md)
- [ ] Frontend design approved (04-FRONTEND.md)
- [ ] Data models approved (05-DATA-MODELS.md)
- [ ] Implementation timeline approved (06-IMPLEMENTATION.md)
- [ ] Gemini AI configuration confirmed (already set up in project)
- [ ] Any scope changes or additions noted

---

## Feedback

Please provide feedback on:

1. **Scope**: Are there features to add or remove?
2. **Priority**: Should certain phases be reordered?
3. **AI Provider**: Which AI provider should be the default?
4. **Timeline**: Is the estimated timeline acceptable?
5. **Design**: Any changes to UI/UX approach?

---

**Document Status**: Complete - Awaiting Approval  
**Created**: 2025-12-14  
**Author**: GitHub Copilot  
**Version**: 1.0
