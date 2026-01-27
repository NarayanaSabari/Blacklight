# DOCX to PDF Conversion - Testing Guide

## Overview
This document provides step-by-step testing procedures for the DOCX to PDF conversion feature.

---

## Prerequisites

### 1. Install Dependencies
```bash
cd server
pip install -r requirements.txt
```

### 2. Install Conversion Tools

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y libreoffice libreoffice-writer
```

**macOS:**
```bash
brew install --cask libreoffice
```

**Windows:**
- Install Microsoft Word (part of Office suite)

### 3. Verify Installation
```bash
# Linux/Mac
which libreoffice || which soffice

# Check version
libreoffice --version
```

---

## Unit Tests

### Test 1: Conversion Availability Check
**Purpose:** Verify the system can detect available conversion tools

```python
cd server
python3 << 'EOF'
from app.utils.docx_converter import DocxToPdfConverter, is_docx_conversion_enabled

print("=== Conversion Availability Test ===")
print(f"System conversion available: {DocxToPdfConverter.is_conversion_available()}")
print(f"Feature enabled: {is_docx_conversion_enabled()}")

# Should print True on Linux/Mac with LibreOffice installed
# Should print False without LibreOffice
EOF
```

**Expected Results:**
- With LibreOffice: Both return `True`
- Without LibreOffice: Both return `False`
- With `ENABLE_DOCX_TO_PDF_CONVERSION=false`: Second returns `False`

---

### Test 2: Platform Detection
**Purpose:** Verify correct platform is detected

```python
cd server
python3 << 'EOF'
from app.utils.docx_converter import SYSTEM_PLATFORM

print(f"Detected platform: {SYSTEM_PLATFORM}")
# Should print: "Linux", "Darwin" (Mac), or "Windows"
EOF
```

---

### Test 3: Manual DOCX to PDF Conversion
**Purpose:** Test conversion with a sample DOCX file

**Create sample DOCX:**
```python
cd server
python3 << 'EOF'
from docx import Document

# Create a simple test resume
doc = Document()
doc.add_heading('John Doe', 0)
doc.add_heading('Software Engineer', level=2)
doc.add_paragraph('Email: john@example.com')
doc.add_paragraph('Phone: (555) 123-4567')
doc.add_heading('Experience', level=2)
doc.add_paragraph('Senior Developer at Tech Corp (2020-2024)')
doc.save('/tmp/test_resume.docx')

print("Created /tmp/test_resume.docx")
EOF
```

**Test conversion:**
```python
cd server
python3 << 'EOF'
from app.utils.docx_converter import DocxToPdfConverter
import os

try:
    # Convert DOCX to PDF
    pdf_path = DocxToPdfConverter.convert_to_pdf(
        '/tmp/test_resume.docx',
        '/tmp/test_resume.pdf'
    )
    
    print(f"✅ Conversion successful: {pdf_path}")
    print(f"✅ PDF exists: {os.path.exists(pdf_path)}")
    print(f"✅ PDF size: {os.path.getsize(pdf_path)} bytes")
    
    # Cleanup
    os.remove('/tmp/test_resume.docx')
    os.remove('/tmp/test_resume.pdf')
    
except Exception as e:
    print(f"❌ Conversion failed: {e}")
EOF
```

**Expected Results:**
- Conversion succeeds
- PDF file is created
- PDF size > 0 bytes
- No errors

---

### Test 4: TextExtractor Integration
**Purpose:** Verify TextExtractor uses conversion automatically

```python
cd server
python3 << 'EOF'
from docx import Document
from app.utils.text_extractor import TextExtractor
import os

# Create test DOCX
doc = Document()
doc.add_heading('Test Resume', 0)
doc.add_paragraph('This is a test resume with some content.')
doc.add_paragraph('Skills: Python, JavaScript, SQL')
doc.save('/tmp/integration_test.docx')

try:
    # Extract text
    result = TextExtractor.extract_from_file('/tmp/integration_test.docx')
    
    print("=== TextExtractor Integration Test ===")
    print(f"✅ Text extracted: {len(result['text'])} characters")
    print(f"✅ Method: {result.get('method', 'unknown')}")
    print(f"✅ Source format: {result.get('source_format', 'unknown')}")
    print(f"\nExtracted text preview:\n{result['text'][:200]}")
    
    # Verify conversion was used
    expected_method = 'pymupdf_from_converted_docx' if 'from_converted_docx' in result['method'] else 'python_docx'
    print(f"\n✅ Used conversion: {'from_converted_docx' in result['method']}")
    
finally:
    if os.path.exists('/tmp/integration_test.docx'):
        os.remove('/tmp/integration_test.docx')
EOF
```

**Expected Results:**
- Text is extracted successfully
- Method includes `from_converted_docx` if conversion is enabled
- Source format is `docx`
- Extracted text contains resume content

---

### Test 5: Fallback Mechanism
**Purpose:** Verify fallback to direct extraction on conversion failure

```python
cd server
python3 << 'EOF'
from app.utils.text_extractor import TextExtractor
from docx import Document
import os

# Create test DOCX
doc = Document()
doc.add_paragraph('Test content for fallback')
doc.save('/tmp/fallback_test.docx')

# Temporarily disable conversion by setting env var
os.environ['ENABLE_DOCX_TO_PDF_CONVERSION'] = 'false'

try:
    result = TextExtractor.extract_from_file('/tmp/fallback_test.docx')
    
    print("=== Fallback Test ===")
    print(f"✅ Extraction succeeded with conversion disabled")
    print(f"✅ Method: {result.get('method', 'unknown')}")
    print(f"✅ Should be python_docx: {result.get('method') == 'python_docx'}")
    
finally:
    os.remove('/tmp/fallback_test.docx')
    os.environ.pop('ENABLE_DOCX_TO_PDF_CONVERSION', None)
EOF
```

**Expected Results:**
- Extraction succeeds even with conversion disabled
- Method is `python_docx` (not converted)
- No errors

---

### Test 6: Temp File Cleanup
**Purpose:** Verify temp files are cleaned up after conversion

```python
cd server
python3 << 'EOF'
from app.utils.text_extractor import TextExtractor
from docx import Document
import os
import glob

# Create test DOCX
doc = Document()
doc.add_paragraph('Test cleanup')
doc.save('/tmp/cleanup_test.docx')

# Count temp PDFs before
before = len(glob.glob('/tmp/resume_*.pdf'))

try:
    result = TextExtractor.extract_from_file('/tmp/cleanup_test.docx')
    
    # Count temp PDFs after (should be same)
    after = len(glob.glob('/tmp/resume_*.pdf'))
    
    print("=== Temp File Cleanup Test ===")
    print(f"✅ Temp PDFs before: {before}")
    print(f"✅ Temp PDFs after: {after}")
    print(f"✅ Cleanup successful: {before == after}")
    
finally:
    os.remove('/tmp/cleanup_test.docx')
EOF
```

**Expected Results:**
- Temp file count remains the same
- No leftover `/tmp/resume_*.pdf` files

---

## Integration Tests

### Test 7: Full Resume Upload Flow
**Purpose:** Test complete end-to-end resume upload and parsing

**Steps:**
1. Start the Flask server:
   ```bash
   cd server
   flask run
   ```

2. Upload a DOCX resume via the portal UI or API:
   ```bash
   # Using curl (replace with actual endpoint and auth)
   curl -X POST http://localhost:5000/api/candidates \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -F "resume=@sample_resume.docx" \
     -F "first_name=John" \
     -F "last_name=Doe"
   ```

3. Check logs for conversion messages:
   ```bash
   # Look for these log messages:
   # "Converting DOCX to PDF for better extraction"
   # "Successfully extracted text via DOCX->PDF conversion"
   ```

4. Verify parsed data in the response/database

**Expected Results:**
- Resume uploads successfully
- Logs show conversion happened
- Parsed data is accurate (name, email, skills, etc.)
- No errors in logs

---

### Test 8: Inngest Resume Parsing Job
**Purpose:** Test Inngest async job with DOCX conversion

**Steps:**
1. Trigger a resume parse event:
   ```python
   from app.inngest import inngest_client
   import inngest
   
   inngest_client.send_sync(
       inngest.Event(
           name="candidate-resume/parse",
           data={
               "resume_id": 123,  # Replace with actual resume ID
               "candidate_id": 456,
               "tenant_id": 1,
               "update_profile": True
           }
       )
   )
   ```

2. Monitor Inngest logs/dashboard

3. Check `candidate_resumes` table for parsed data

**Expected Results:**
- Job completes successfully
- `processing_status` changes: `pending` → `processing` → `completed`
- `parsed_resume_data` contains extracted information
- No job failures

---

### Test 9: Public Onboarding Resume Upload
**Purpose:** Test resume upload via public onboarding form

**Steps:**
1. Create a public invitation link
2. Fill out onboarding form
3. Upload DOCX resume
4. Submit form

**Expected Results:**
- Resume uploads without errors
- Resume is parsed correctly
- Candidate record is created with parsed data

---

## Edge Case Tests

### Test 10: Large DOCX File
**Purpose:** Test with large resume (>5MB)

```bash
# Create a large DOCX (add images, etc.)
# Upload via portal
# Verify: Should complete within 60 seconds or fallback
```

**Expected Results:**
- Completes successfully (if < 60s)
- OR falls back to direct extraction (if > 60s)
- No crashes or hangs

---

### Test 11: Password-Protected DOCX
**Purpose:** Verify graceful handling of protected files

```bash
# Create a password-protected DOCX
# Upload via portal
# Verify: Falls back to direct extraction or shows error
```

**Expected Results:**
- Conversion fails gracefully
- Falls back to direct extraction (may also fail)
- Error is logged, not exposed to user
- System remains stable

---

### Test 12: Corrupted DOCX File
**Purpose:** Test with corrupted/invalid DOCX

```bash
# Create an invalid DOCX (rename a .txt to .docx)
echo "This is not a valid DOCX" > /tmp/fake.docx

# Try to extract
python3 -c "
from app.utils.text_extractor import TextExtractor
result = TextExtractor.extract_from_file('/tmp/fake.docx')
print(result)
"
```

**Expected Results:**
- Conversion fails
- Falls back to direct extraction
- Error is logged
- Returns empty text or error message
- No crashes

---

### Test 13: DOCX with Tables
**Purpose:** Verify tables are extracted correctly

**Create test DOCX with table:**
```python
from docx import Document
from docx.shared import Inches

doc = Document()
doc.add_heading('Resume with Table', 0)

# Add table
table = doc.add_table(rows=3, cols=3)
table.style = 'Table Grid'

# Fill table
cells = table.rows[0].cells
cells[0].text = 'Company'
cells[1].text = 'Role'
cells[2].text = 'Years'

cells = table.rows[1].cells
cells[0].text = 'Tech Corp'
cells[1].text = 'Engineer'
cells[2].text = '2020-2024'

doc.save('/tmp/table_test.docx')

# Extract and verify
from app.utils.text_extractor import TextExtractor
result = TextExtractor.extract_from_file('/tmp/table_test.docx')
print(result['text'])

# Check if table data is present
assert 'Tech Corp' in result['text']
assert 'Engineer' in result['text']
```

**Expected Results:**
- Table content is extracted
- Cell values are present in text
- Table structure is reasonably preserved

---

### Test 14: Multi-Column DOCX
**Purpose:** Test complex layouts with multiple columns

**Expected Results:**
- Text from all columns is extracted
- Reading order is logical
- No text is lost

---

### Test 15: DOCX with Images
**Purpose:** Verify images don't break extraction

**Expected Results:**
- Images are ignored (text extraction only)
- No errors
- Text around images is extracted

---

## Performance Tests

### Test 16: Conversion Speed
**Purpose:** Measure conversion time for various file sizes

```python
import time
from app.utils.docx_converter import DocxToPdfConverter

# Test multiple files
test_files = [
    ('/tmp/small.docx', 'Small (< 100KB)'),
    ('/tmp/medium.docx', 'Medium (500KB - 1MB)'),
    ('/tmp/large.docx', 'Large (> 5MB)')
]

for file_path, label in test_files:
    if not os.path.exists(file_path):
        continue
    
    start = time.time()
    try:
        DocxToPdfConverter.convert_to_pdf(file_path, f'{file_path}.pdf')
        elapsed = time.time() - start
        print(f"{label}: {elapsed:.2f} seconds")
    except Exception as e:
        print(f"{label}: FAILED - {e}")
```

**Expected Results:**
- Small: < 3 seconds
- Medium: 3-7 seconds
- Large: 5-15 seconds (may timeout at 60s)

---

### Test 17: Concurrent Conversions
**Purpose:** Test multiple simultaneous conversions

```python
import concurrent.futures
from app.utils.docx_converter import DocxToPdfConverter

def convert_file(index):
    # Create and convert test file
    # Return time taken
    pass

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(convert_file, i) for i in range(5)]
    results = [f.result() for f in futures]

print(f"Concurrent conversions: {len([r for r in results if r is not None])} succeeded")
```

**Expected Results:**
- All conversions complete
- No crashes or race conditions
- Temp files are properly isolated

---

## Regression Tests

### Test 18: PDF Files Still Work
**Purpose:** Ensure PDF processing is unchanged

```bash
# Upload a PDF resume
# Verify: Processes as before, no conversion attempted
```

**Expected Results:**
- PDF uploads work as before
- No conversion logs
- Direct PDF extraction used

---

### Test 19: DOC Files Still Work
**Purpose:** Ensure old .doc format works

```bash
# Upload a .doc resume
# Verify: Uses antiword extractor
```

**Expected Results:**
- DOC files work as before
- Uses `antiword` extractor
- No regression

---

## Configuration Tests

### Test 20: Disabled Conversion
**Purpose:** Test with feature disabled

```bash
# Set ENABLE_DOCX_TO_PDF_CONVERSION=false
# Upload DOCX resume
# Verify: Uses direct extraction, no conversion logs
```

**Expected Results:**
- Feature respects config flag
- Direct extraction used
- No conversion attempted

---

### Test 21: Config Hot-Reload
**Purpose:** Verify config changes take effect without restart

```bash
# Upload DOCX with conversion enabled
# Change env var to false
# Upload another DOCX
# Verify: Second uses direct extraction
```

**Expected Results:**
- Config changes are detected
- Behavior changes without restart

---

## Production Readiness Checklist

### Before Deployment:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Edge cases handled gracefully
- [ ] Performance is acceptable
- [ ] Logs are informative and not excessive
- [ ] Temp files are cleaned up
- [ ] Configuration works as expected
- [ ] Documentation is complete
- [ ] LibreOffice installed on production server
- [ ] Monitoring/alerting configured (optional)

---

## Troubleshooting Test Failures

### Conversion Not Available
**Fix:** Install LibreOffice or set `ENABLE_DOCX_TO_PDF_CONVERSION=false`

### Conversion Timeout
**Fix:** Increase timeout in `docx_converter.py` or use smaller test files

### Import Errors
**Fix:** Ensure virtual environment is active and dependencies installed:
```bash
pip install -r requirements.txt
```

### Temp File Errors
**Fix:** Check `/tmp` directory permissions:
```bash
ls -la /tmp
# Should be writable
```

---

## Automated Testing

### Future: Add Pytest Tests

Create `/server/tests/test_docx_conversion.py`:

```python
import pytest
from app.utils.docx_converter import DocxToPdfConverter, is_docx_conversion_enabled
from app.utils.text_extractor import TextExtractor

class TestDocxConversion:
    def test_conversion_availability(self):
        # Test platform detection
        assert isinstance(DocxToPdfConverter.is_conversion_available(), bool)
    
    def test_conversion_with_sample_file(self, sample_docx):
        # Test actual conversion
        pdf_path = DocxToPdfConverter.convert_to_pdf(sample_docx)
        assert os.path.exists(pdf_path)
    
    def test_text_extraction_integration(self, sample_docx):
        # Test TextExtractor integration
        result = TextExtractor.extract_from_file(sample_docx)
        assert 'text' in result
        assert len(result['text']) > 0
    
    def test_fallback_on_failure(self, corrupted_docx):
        # Test fallback mechanism
        result = TextExtractor.extract_from_file(corrupted_docx)
        # Should not crash, may return empty text
        assert isinstance(result, dict)
```

Run with:
```bash
pytest tests/test_docx_conversion.py -v
```

---

## Test Summary Report Template

```
# DOCX Conversion Test Results

**Date:** YYYY-MM-DD
**Tester:** [Name]
**Environment:** [Development/Staging/Production]

## Unit Tests
- [ ] Test 1: Conversion availability
- [ ] Test 2: Platform detection
- [ ] Test 3: Manual conversion
- [ ] Test 4: TextExtractor integration
- [ ] Test 5: Fallback mechanism
- [ ] Test 6: Temp file cleanup

## Integration Tests
- [ ] Test 7: Full resume upload
- [ ] Test 8: Inngest job
- [ ] Test 9: Public onboarding

## Edge Cases
- [ ] Test 10: Large files
- [ ] Test 11: Password-protected
- [ ] Test 12: Corrupted files
- [ ] Test 13: Tables
- [ ] Test 14: Multi-column
- [ ] Test 15: Images

## Performance
- [ ] Test 16: Conversion speed
- [ ] Test 17: Concurrent conversions

## Regression
- [ ] Test 18: PDF files
- [ ] Test 19: DOC files

## Configuration
- [ ] Test 20: Disabled conversion
- [ ] Test 21: Config hot-reload

## Issues Found
[List any issues discovered]

## Recommendations
[List recommendations for improvement]

## Sign-off
- [ ] All critical tests passed
- [ ] Ready for production deployment
```

---

## Contact

For questions or issues with testing, contact the development team or refer to `/server/docs/RESUME_PARSING.md`.
