# Resume Parsing - DOCX to PDF Conversion

## Overview

Blacklight now automatically converts DOCX files to PDF before text extraction to improve parsing accuracy. This feature addresses issues with unreliable DOCX text extraction and provides better results for resume parsing.

## Why DOCX Conversion?

### Problem with Direct DOCX Extraction
- `python-docx` doesn't preserve layout/formatting well
- Tables can be misaligned or lose structure
- Header/footer extraction is unreliable
- Complex formatting causes text jumbling
- Inconsistent results across different DOCX formats

### Benefits of PDF Extraction
- PyMuPDF extracts text with layout preserved
- pdfplumber handles tables/columns better
- More consistent results across formats
- Better handling of multi-column layouts
- Improved section detection

### Performance Trade-off
- Conversion adds ~2-5 seconds per resume
- Acceptable trade-off for significantly better accuracy
- Can be disabled via configuration if needed

## Installation

### Windows
**Requires Microsoft Word installed** (uses COM API)

```bash
pip install docx2pdf
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y libreoffice libreoffice-writer
pip install docx2pdf
```

### macOS
```bash
brew install --cask libreoffice
pip install docx2pdf
```

### Docker Deployment
Add to your Dockerfile:

```dockerfile
# Install LibreOffice for DOCX conversion
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*
```

## Configuration

### Environment Variable
Add to `.env` or `.env.production`:

```bash
# Enable/disable DOCX to PDF conversion
ENABLE_DOCX_TO_PDF_CONVERSION=true
```

**Default:** `true` (enabled)

**When to disable:**
- LibreOffice/MS Word not available
- Faster processing needed (trade accuracy for speed)
- Testing direct DOCX extraction
- Known issues with conversion on specific environment

### Checking Status
```python
from app.utils.docx_converter import is_docx_conversion_enabled

if is_docx_conversion_enabled():
    print("DOCX conversion is available")
else:
    print("DOCX conversion is disabled or tools not available")
```

## How It Works

### Automatic Conversion Flow

```
DOCX File Upload
    ↓
TextExtractor.extract_from_file()
    ↓
Check: is_docx_conversion_enabled()
    ├─ True → Convert DOCX to temp PDF
    │         ↓
    │    Extract text from PDF (PyMuPDF/pdfplumber)
    │         ↓
    │    Cleanup temp PDF file
    │         ↓
    │    Return text with metadata:
    │      - method: 'pymupdf_from_converted_docx'
    │      - source_format: 'docx'
    │
    └─ False → Direct DOCX extraction (python-docx)
           ↓
      Return text with metadata:
        - method: 'python_docx'
        - source_format: 'docx'
```

### Fallback Strategy
If conversion fails (corrupted file, password-protected, timeout):
1. Log the error
2. Automatically fall back to direct DOCX extraction
3. Continue processing without user intervention

### Platform-Specific Conversion

**Windows:**
- Uses `docx2pdf` library with MS Word COM API
- Requires Microsoft Word installed
- Best quality conversion

**Linux/Mac:**
- Uses LibreOffice command-line interface
- Command: `soffice --headless --convert-to pdf`
- 60-second timeout per conversion
- Requires LibreOffice installation

## Usage

### Automatic (Recommended)
All resume uploads automatically use DOCX conversion when enabled. No code changes needed.

**Affected endpoints:**
- `POST /api/candidates` (with resume upload)
- `POST /api/candidates/{id}/resume` (resume replacement)
- `POST /api/onboarding/submit` (public onboarding)
- Inngest job: `candidate-resume/parse`

### Programmatic Usage

```python
from app.utils.docx_converter import DocxToPdfConverter

# Convert DOCX to PDF (specify output path)
pdf_path = DocxToPdfConverter.convert_to_pdf(
    docx_path='resume.docx',
    output_path='resume.pdf',
    cleanup_source=False  # Keep original DOCX
)

# Convert to temporary PDF (auto-generated path)
temp_pdf = DocxToPdfConverter.convert_to_temp_pdf('resume.docx')
# ... use temp_pdf ...
os.remove(temp_pdf)  # Cleanup when done

# Check if conversion is available
if DocxToPdfConverter.is_conversion_available():
    # Conversion tools are installed
    pass
```

## Troubleshooting

### Conversion Not Available

**Symptom:** `is_docx_conversion_enabled()` returns `False`

**Causes:**
1. `ENABLE_DOCX_TO_PDF_CONVERSION=false` in environment
2. LibreOffice not installed (Linux/Mac)
3. Microsoft Word not installed (Windows)

**Solutions:**
- Set `ENABLE_DOCX_TO_PDF_CONVERSION=true`
- Install LibreOffice (see Installation section)
- Verify installation: `which libreoffice` or `which soffice`

### Conversion Timeout

**Symptom:** Logs show "LibreOffice conversion timed out after 60 seconds"

**Causes:**
- Very large DOCX files (>10MB)
- Complex DOCX with many images/objects
- System resource constraints

**Solutions:**
- Falls back to direct extraction automatically
- Consider increasing timeout in `docx_converter.py` (line 173)
- Check system resources (CPU, memory)

### Conversion Fails

**Symptom:** Logs show conversion errors, but parsing continues

**Common errors:**
- Password-protected DOCX → Falls back to direct extraction
- Corrupted DOCX → Falls back to direct extraction
- LibreOffice crash → Falls back to direct extraction

**What happens:**
- Error is logged
- System automatically uses direct DOCX extraction
- User sees no error (seamless fallback)

### Temp File Cleanup Issues

**Symptom:** Leftover `/tmp/resume_*.pdf` files

**Causes:**
- Process crash before cleanup
- Exception during processing

**Solutions:**
- Temp files use prefix `resume_` for easy cleanup
- Add cron job: `find /tmp -name "resume_*.pdf" -mtime +1 -delete`
- Files in `/tmp` are typically cleared on reboot

## Monitoring

### Log Messages

**Successful conversion:**
```
[INFO] Converting DOCX to PDF: /tmp/resume_abc123.docx -> /tmp/resume_abc123.pdf
[INFO] DOCX converted successfully: /tmp/resume_abc123.pdf
[INFO] Extracting text from DOCX file using PDF conversion
```

**Fallback to direct extraction:**
```
[WARNING] DOCX to PDF conversion failed: [error details]
[INFO] Falling back to direct DOCX extraction
[INFO] Extracting text from DOCX file using python-docx
```

**Configuration disabled:**
```
[INFO] DOCX to PDF conversion disabled via configuration
[INFO] Extracting text from DOCX file using python-docx
```

### Metrics to Track

Consider adding metrics for:
- Conversion success rate (%)
- Average conversion time (seconds)
- Fallback rate (%)
- File sizes processed (MB)
- Extraction method distribution (PDF vs direct)

## Security Considerations

### File Handling
- Temp files created with secure permissions
- Cleanup handled in `finally` blocks
- Files stored in system temp directory (`/tmp`)

### Malicious Files
- Timeout prevents infinite loops (60 seconds)
- LibreOffice runs in `--headless` mode (no GUI)
- Conversion happens in isolated process
- Falls back gracefully on suspicious files

### Resource Limits
- Single conversion timeout: 60 seconds
- No batch conversion (one file at a time)
- Temp files auto-deleted after use

## Performance Optimization

### Current Performance
- Conversion: 2-5 seconds per DOCX
- PDF extraction: 0.5-2 seconds
- **Total overhead:** ~3-7 seconds per resume

### Future Optimizations
1. **Caching:** Cache converted PDFs to avoid re-conversion
2. **Batch Processing:** Convert multiple files in parallel
3. **Async Conversion:** Run conversion in background worker
4. **Format Detection:** Skip conversion for simple DOCX files

## Testing

### Manual Testing

**Test conversion availability:**
```bash
cd server
python3 -c "from app.utils.docx_converter import DocxToPdfConverter; print(DocxToPdfConverter.is_conversion_available())"
```

**Test full flow:**
1. Upload a `.docx` resume via portal
2. Check logs for conversion messages
3. Verify parsed data is accurate
4. Compare with direct DOCX extraction results

### Test Cases

**Positive cases:**
- Simple DOCX with text only
- DOCX with tables
- DOCX with multi-column layout
- DOCX with headers/footers
- Large DOCX (>5MB)

**Edge cases:**
- Password-protected DOCX (should fallback)
- Corrupted DOCX (should fallback)
- DOCX with embedded images (should work)
- Very large DOCX >10MB (may timeout)
- DOCX from different MS Word versions

**Configuration tests:**
- With `ENABLE_DOCX_TO_PDF_CONVERSION=true`
- With `ENABLE_DOCX_TO_PDF_CONVERSION=false`
- Without LibreOffice installed
- With LibreOffice installed

## Migration Notes

### Existing Resumes
- Previously parsed resumes are NOT automatically re-parsed
- New resume uploads will use conversion
- To re-parse existing resumes, trigger `candidate-resume/parse` event

### Backward Compatibility
- Feature is fully backward compatible
- No changes required to existing code
- Falls back to old behavior if conversion unavailable
- Can be disabled via environment variable

## FAQ

**Q: Will this slow down resume uploads?**
A: Yes, by ~2-5 seconds per resume. This is an acceptable trade-off for better accuracy.

**Q: What if LibreOffice is not installed?**
A: System automatically falls back to direct DOCX extraction using `python-docx`.

**Q: Can I disable this feature?**
A: Yes, set `ENABLE_DOCX_TO_PDF_CONVERSION=false` in your `.env` file.

**Q: Does this affect PDF uploads?**
A: No, PDF uploads are processed as before (no conversion needed).

**Q: What about .DOC files (old Word format)?**
A: .DOC files are handled by `antiword` extractor, not affected by this change.

**Q: Will temp files fill up disk space?**
A: No, temp files are automatically deleted after use. System `/tmp` is typically cleared on reboot.

**Q: Can I use this for non-resume documents?**
A: Yes, `TextExtractor.extract_from_file()` works for any DOCX file.

## Support

### Logs Location
- Development: Console output
- Production: `/var/log/blacklight/app.log`

### Debug Mode
Enable detailed logging:
```python
import logging
logging.getLogger('app.utils.docx_converter').setLevel(logging.DEBUG)
logging.getLogger('app.utils.text_extractor').setLevel(logging.DEBUG)
```

### Reporting Issues
Include:
1. DOCX file details (size, Word version)
2. Platform (Windows/Linux/Mac)
3. LibreOffice version: `libreoffice --version`
4. Error logs
5. Whether fallback succeeded
