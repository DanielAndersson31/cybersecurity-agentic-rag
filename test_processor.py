from database.document_processor import process_pdf, chunk_text

# Test with one of your PDFs
pdf_path = "data/raw/incident_reponse/Computer Security Incident Handling Guide - NIST.SP.800-61r2.pdf"  # Adjust filename
text = process_pdf(pdf_path)



print(f"Extracted {len(text)} characters")
print("First 200 characters:")
print(text[:200])

# Test chunking
chunks = chunk_text(text[:5000])  # Just test with first 5000 chars
print(f"\nCreated {len(chunks)} chunks")
print(f"First chunk: {len(chunks[0])} characters")