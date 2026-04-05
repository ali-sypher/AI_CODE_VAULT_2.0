import os
import io
import csv
import PyPDF2
import docx

def extract_text_from_file(uploaded_file, file_type):
    """Extracts raw text from various file formats."""
    text = ""
    try:
        if file_type == 'pdf':
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif file_type == 'docx':
            doc = docx.Document(uploaded_file)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        elif file_type == 'csv':
            # Decode bytes to string
            content = uploaded_file.getvalue().decode('utf-8')
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                text += " ".join(row) + "\n"
        elif file_type in ['txt', 'py', 'md']:
            content = uploaded_file.getvalue().decode('utf-8')
            text = content
    except Exception as e:
        print(f"Error extracting text from {file_type}: {str(e)}")
    return text

def chunk_text(text, chunk_size=800, overlap=100):
    """Splits text into chunks of specified size with overlap."""
    if not text:
        return []
    
    words = text.split()
    chunks = []
    
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1 # +1 for space
        
        if current_length >= chunk_size:
            chunks.append(" ".join(current_chunk))
            # Keep the last 'overlap' words for the next chunk
            if overlap > 0 and len(current_chunk) > overlap_words(overlap):
                current_chunk = current_chunk[-overlap_words(overlap):]
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk = []
                current_length = 0
                
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def overlap_words(overlap_chars, avg_word_len=5):
    return max(1, overlap_chars // avg_word_len)
