import fitz
import re

def extract_text_from_file(doc_instance):
    ext = doc_instance.extension.lower()
    file_path = doc_instance.file.path
    if ext == 'pdf':
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    return text

def samples_to_text(samples):
    """
    Converts a list of {'question': ..., 'expected_answer': ...} dicts
    into a readable text blob suitable for storage or display.
    """
    return "\n\n".join(
        f"Q: {sample.get('question')}\nA: {sample.get('expected_answer')}"
        for sample in samples
    )

def split_qa_pairs(text):
    # Split text by double newlines to get each Q&A block
    qa_blocks = [block.strip() for block in text.strip().split('\n\n') if block.strip()]
    return qa_blocks

def deduplicate_qa_blocks(blocks):
    seen = set()
    deduped = []
    for block in blocks:
        if block not in seen:
            deduped.append(block)
            seen.add(block)
    return deduped

def deduplicate_by_question(text):
    # Split into Q&A blocks
    qa_blocks = [block.strip() for block in text.strip().split('\n\n') if block.strip()]
    seen_questions = set()
    deduped_blocks = []
    for block in qa_blocks:
        match = re.match(r"Q:\s*(.+)", block)
        question = None
        if match:
            question = match.group(1).strip()
        else:
            # Fallback: split at newline if not matching exactly
            question = block.split('\n')[0].replace("Q:", "").strip()
        if question and question not in seen_questions:
            deduped_blocks.append(block)
            seen_questions.add(question)
    return "\n\n".join(deduped_blocks)


def chunk_text(text: str, chunk_size: int = 500) -> list:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks