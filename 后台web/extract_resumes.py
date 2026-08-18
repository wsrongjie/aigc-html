import os
import PyPDF2

resume_dir = r"C:\Users\wsrji\Downloads\简历库"

all_files = os.listdir(resume_dir)
pdf_files = [f for f in all_files if f.lower().endswith('.pdf')]

saas_files = [f for f in pdf_files if 'saas' in f.lower() and '12-20K' in f]

print(f"Found {len(saas_files)} saas files")

output_file = r"C:\Users\wsrji\Desktop\AIGC\AI视频原型\3.0b版本\后台web\extracted_resumes.txt"

with open(output_file, 'w', encoding='utf-8') as out:
    for filename in saas_files:
        filepath = os.path.join(resume_dir, filename)
        out.write(f"\n{'='*80}\n")
        out.write(f"FILE: {filename}\n")
        out.write(f"{'='*80}\n")
        
        try:
            with open(filepath, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                
                out.write(text)
                out.write(f"\n{'='*80}\n")
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            out.write(error_msg + "\n")
            print(f"Error reading {filename}: {e}")

print(f"Done. Results saved to {output_file}")
