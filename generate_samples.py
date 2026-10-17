"""
Generate realistic corrupted and distorted sample test files for Unifile by Soniscorett.
"""

import os
import base64
import json
from pathlib import Path
import docx
import openpyxl
from pypdf import PdfWriter

SAMPLES_DIR = Path("/home/user/unifile/samples")
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Mojibake Latin-1 distortion sample
mojibake_text = (
    "RAPPORT CONFIDENTIEL DE SÃ‰CURITÃ‰ - SONISCORETT LABS\n\n"
    "L'Ã©quipe d'ingÃ©nierie a dÃ©tectÃ© des problÃ¨mes de compatibilitÃ© majeurs dans le systÃ¨me hÃ©ritÃ©.\n"
    "Les paramÃ¨tres ont Ã©tÃ© modifiÃ©s conformÃ©ment aux rÃ¨gles de conformitÃ© europÃ©enne (RGPD).\n"
    "Le coÃ»t estimÃ© s'Ã©lÃ¨ve Ã\xa0 120 000 â‚¬ (cent vingt mille euros).\n"
    "Veuillez valider l'intÃ©gritÃ© des donnÃ©es avant la synchronisation des modÃ¨les IA.\n"
    "Statut de l'opÃ©ration: SUCCÃˆS GARANTI Ã\xa0 100%."
)
with open(SAMPLES_DIR / "mojibake_latin1_sample.txt", "w", encoding="utf-8") as f:
    f.write(mojibake_text)

# 2. Zalgo, zero-width, homoglyph and symbol noise sample
zalgo_text = (
    "U̶n̴i̶f̵i̵l̸e̷ ̶B̶y̸ ̶S̴o̶n̸i̴s̵c̶o̵r̸e̴t̶t̶:̶ ̶U̸l̴t̴i̸m̵a̷t̶e̶ ̷R̶e̸s̵t̶o̸r̸a̵t̷i̶o̵n̶ ̶P̴r̷o̷t̶o̷c̴o̵l̵\n\n"
    "Th\u200be s\u200bys\u200bte\u200bm o\u200bp\u200be\u200bra\u200bti\u200bo\u200bn\u200bal p\u200ba\u200br\u200ba\u200bm\u200be\u200bt\u200be\u200br\u200bs a\u200br\u200be f\u200bu\u200bl\u200bl\u200by v\u200be\u200br\u200bi\u200bf\u200bi\u200be\u200bd.\n"
    "A*u*t*h*e*n*t*i*c*a*t*i*o*n token verification across distributed neural clusters.\n"
    "All telemetry streams remain strictly encrypted and non-destructive for read-only agent connectors.\n"
    "Readability rating guaranteed above eighty percent threshold in all user target dialects.\n"
)
with open(SAMPLES_DIR / "zalgo_symbol_corrupted.txt", "w", encoding="utf-8") as f:
    f.write(zalgo_text)

# 3. Encrypted Base64, Hex & ROT-13 payload
secret_contract_body = "CONFIDENTIAL PARTNERSHIP AGREEMENT: Soniscorett shall provide AI models with universal read-only connector pipelines, guaranteeing at least eighty percent readability on all ingested enterprise documents."
b64_block = base64.b64encode(secret_contract_body.encode("utf-8")).decode("ascii")

contract_text = (
    "DOCUMENT IDENTIFIER: CONTRACT-2026-ALPHA\n"
    "CLASSIFICATION: RESTRICTED ACCESS\n\n"
    "EXECUTIVE SUMMARY:\n"
    "The client requires safe parsing of distorted multi-source data files.\n\n"
    "ENCRYPTED CLAUSE 4.2 (BASE64):\n"
    f"data:text/plain;base64,{b64_block}\n\n"
    "TECHNICAL APPENDIX (HEXADECIMAL DUMP):\n"
    "48 65 61 6c 74 68 79 20 53 79 73 74 65 6d 20 53 74 61 74 75 73 20 4f 4b\n\n"
    "TERMINATION NOTICE: Both parties agree to open-source connector licensing under MIT terms."
)
with open(SAMPLES_DIR / "encrypted_base64_hex_contract.txt", "w", encoding="utf-8") as f:
    f.write(contract_text)

# 4. Truncated broken JSON
truncated_json = """{
  "system": "Soniscorett Unifile Universal Connector",
  "version": "2.4.0",
  "health": "operational",
  "read_only": true,
  "cluster_nodes": [
    {"node_id": "us-east-1a", "status": "active", "latency_ms": 12.4},
    {"node_id": "eu-central-1", "status": "active", "latency_ms": 19.8},
    {"node_id": "ap-southeast-1", "status": "syncing", "payload": "Interconnecting neural model bridge with automatic truncation recovery and syntax healing
"""
with open(SAMPLES_DIR / "truncated_broken_json.json", "w", encoding="utf-8") as f:
    f.write(truncated_json)

# 5. Multilingual garbled Spanish specification
spanish_garbled = (
    "ESPECIFICACIÃ“N DEL SISTEMA UNIFILE POR SONISCORETT\n\n"
    "Este conector universal de solo lectura permite a los modelos de inteligencia artificial procesar cualquier archivo.\n"
    "Detecta y elimina automÃ¡ticamente distorsiones, texto encriptado, archivos truncados y sÃ\xadmbolos corruptos.\n"
    "Garantiza que el texto final sea al menos 80% legible en el idioma preferido del usuario.\n"
    "El sistema no modifica los archivos originales y protege la seguridad del entorno.\n"
    "Resultado final: documento completamente limpio, traducido y optimizado para LLMs."
)
with open(SAMPLES_DIR / "multilingual_garbled_spec.txt", "w", encoding="utf-8") as f:
    f.write(spanish_garbled)

# 6. Real Word .docx file
doc = docx.Document()
doc.add_heading("Soniscorett Enterprise Audit Report", 0)
doc.add_paragraph("L'Ã©quipe d'analyse a constatÃ© des rÃ©sultats exceptionnels sur le connecteur universel Unifile.")
doc.add_paragraph("This document contains multi-tier security logs and metrics.")
table = doc.add_table(rows=1, cols=3)
hdr = table.rows[0].cells
hdr[0].text = "ID"
hdr[1].text = "Module"
hdr[2].text = "Readability Guarantee"
r1 = table.add_row().cells
r1[0].text = "MOD-01"
r1[1].text = "Mojibake & Distortion Healer"
r1[2].text = ">= 80% Readable (Passed)"
r2 = table.add_row().cells
r2[0].text = "MOD-02"
r2[1].text = "Universal Parser Read-Only"
r2[2].text = "100% Non-destructive"
doc.save(SAMPLES_DIR / "sample_report.docx")

# 7. Real Excel .xlsx file
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Telemetry Data"
ws.append(["Metric ID", "Component", "Health Status", "Initial Score", "Post-Heal Readability"])
ws.append(["T-101", "De-obfuscator Engine", "Active", "35%", "96.5%"])
ws.append(["T-102", "Syntax Bracket Healer", "Active", "42%", "94.0%"])
ws.append(["T-103", "Zalgo Stripper", "Active", "28%", "98.2%"])
ws.append(["T-104", "Universal Translator", "Active", "50%", "92.8%"])
wb.save(SAMPLES_DIR / "sample_data.xlsx")

# 8. Real PDF Document
# Create a valid PDF with ReportLab containing actual text lines and metadata
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas(str(SAMPLES_DIR / "sample_document.pdf"), pagesize=letter)
c.setTitle("Unifile Universal AI Document")
c.setAuthor("Soniscorett Labs")
c.setSubject("Read-Only AI Connector Telemetry and Corruption Recovery")
c.setFont("Helvetica-Bold", 16)
c.drawString(100, 700, "Unifile Universal AI Document")
c.setFont("Helvetica", 12)
c.drawString(100, 670, "Soniscorett Labs")
c.drawString(100, 640, "Read-Only AI Connector Telemetry and Corruption Recovery")
c.save()

print(f"Generated {len(list(SAMPLES_DIR.glob('*')))} sample test files successfully.")
