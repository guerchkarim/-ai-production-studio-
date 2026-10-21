"""Bounded document extraction, launched in a subprocess by the API."""
import io
import sys
import zipfile
from pathlib import Path

try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))
except ImportError:
    pass  # Windows: the parent process still enforces a 30 second timeout.

path=Path(sys.argv[1])
if path.suffix=='.pdf':
    from pypdf import PdfReader
    reader=PdfReader(path)
    if reader.is_encrypted:raise ValueError('PDF chiffré non pris en charge')
    if len(reader.pages)>500:raise ValueError('500 pages maximum')
    parts=[];size=0
    for page in reader.pages:
        text=page.extract_text() or '';size+=len(text)
        if size>200000:raise ValueError('200000 caractères maximum')
        parts.append(text)
    result='\n\n'.join(parts)
elif path.suffix=='.docx':
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist())>2000 or sum(i.file_size for i in archive.infolist())>50*1024*1024:raise ValueError('Document DOCX trop volumineux')
    from docx import Document
    document=Document(path)
    result='\n\n'.join(p.text for p in document.paragraphs if p.text.strip())
    if len(result)>200000:raise ValueError('200000 caractères maximum')
else:raise ValueError('Format non pris en charge')
if not result.strip():raise ValueError('Aucun texte extractible. Un PDF scanné nécessite un OCR séparé.')
sys.stdout.reconfigure(encoding='utf-8')
sys.stdout.write(result)
