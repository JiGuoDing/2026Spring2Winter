from pypdf import PdfReader

reader = PdfReader("make-08-00030.pdf")
print("pages", len(reader.pages))
parts = []
for i, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    parts.append(f"\n\n===== PAGE {i + 1} =====\n{text}")

content = "".join(parts)
with open("make-08-00030.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("chars", len(content))
