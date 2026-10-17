from pathlib import Path
import json

GT_DIR = Path("/home/user/unifile/samples/ground_truth")
GT_DIR.mkdir(parents=True, exist_ok=True)

references = {
    "mojibake_latin1_reference.txt": (
        "RAPPORT CONFIDENTIEL DE SÉCURITÉ - SONISCORETT LABS\n\n"
        "L'équipe d'ingénierie a détecté des problèmes de compatibilité majeurs dans le système hérité.\n"
        "Les paramètres ont été modifiés conformément aux règles de conformité européenne (RGPD).\n"
        "Le coût estimé s'élève à 120 000 € (cent vingt mille euros).\n"
        "Veuillez valider l'intégrité des données avant la synchronisation des modèles IA.\n"
        "Statut de l'opération: SUCCÈS GARANTI à 100%."
    ),
    "zalgo_symbol_reference.txt": (
        "Unifile By Soniscorett: Ultimate Restoration Protocol\n\n"
        "The system operational parameters are fully verified.\n"
        "Authentication token verification across distributed neural clusters.\n"
        "All telemetry streams remain strictly encrypted and non-destructive for read-only agent connectors.\n"
        "Readability rating guaranteed above eighty percent threshold in all user target dialects."
    ),
    "encrypted_contract_reference.txt": (
        "DOCUMENT IDENTIFIER: CONTRACT-2026-ALPHA\n"
        "CLASSIFICATION: RESTRICTED ACCESS\n\n"
        "EXECUTIVE SUMMARY:\n"
        "The client requires safe parsing of distorted multi-source data files.\n\n"
        "ENCRYPTED CLAUSE 4.2 (BASE64):\n"
        "CONFIDENTIAL PARTNERSHIP AGREEMENT: Soniscorett shall provide AI models with universal read-only connector pipelines, guaranteeing at least eighty percent readability on all ingested enterprise documents.\n\n"
        "TECHNICAL APPENDIX (HEXADECIMAL DUMP):\n"
        "Healthy System Status OK\n\n"
        "TERMINATION NOTICE: Both parties agree to open-source connector licensing under MIT terms."
    ),
    "truncated_json_reference.txt": (
        "{\n"
        '  "system": "Soniscorett Unifile Universal Connector",\n'
        '  "version": "2.4.0",\n'
        '  "health": "operational",\n'
        '  "read_only": true,\n'
        '  "cluster_nodes": [\n'
        "    {\n"
        '      "node_id": "us-east-1a",\n'
        '      "status": "active",\n'
        '      "latency_ms": 12.4\n'
        "    },\n"
        "    {\n"
        '      "node_id": "eu-central-1",\n'
        '      "status": "active",\n'
        '      "latency_ms": 19.8\n'
        "    },\n"
        "    {\n"
        '      "node_id": "ap-southeast-1",\n'
        '      "status": "syncing",\n'
        '      "payload": "Interconnecting neural model bridge with automatic truncation recovery and syntax healing"\n'
        "    }\n"
        "  ]\n"
        "}"
    ),
    "multilingual_spec_reference.txt": (
        "ESPECIFICACIÓN DEL SISTEMA UNIFILE POR SONISCORETT\n\n"
        "Este conector universal de solo lectura permite a los modelos de inteligencia artificial procesar cualquier archivo.\n"
        "Detecta y elimina automáticamente distorsiones, texto encriptado, archivos truncados y símbolos corruptos.\n"
        "Garantiza que el texto final sea al menos 80% legible en el idioma preferido del usuario.\n"
        "El sistema no modifica los archivos originales y protege la seguridad del entorno.\n"
        "Resultado final: documento completamente limpio, traducido y optimizado para LLMs."
    ),
    "sample_report_reference.txt": (
        "Soniscorett Enterprise Audit Report\n\n"
        "L'équipe d'analyse a constaté des résultats exceptionnels sur le connecteur universel Unifile.\n\n"
        "This document contains multi-tier security logs and metrics.\n\n"
        "ID | Module | Readability Guarantee\n\n"
        "MOD-01 | Mojibake & Distortion Healer | >= 80% Readable (Passed)\n\n"
        "MOD-02 | Universal Parser Read-Only | 100% Non-destructive"
    ),
    "sample_data_reference.txt": (
        "### Sheet: Telemetry Data\n"
        "Metric ID | Component | Health Status | Initial Score | Post-Heal Readability\n"
        "T-101 | De-obfuscator Engine | Active | 35% | 96.5%\n"
        "T-102 | Syntax Bracket Healer | Active | 42% | 94.0%\n"
        "T-103 | Zalgo Stripper | Active | 28% | 98.2%\n"
        "T-104 | Universal Translator | Active | 50% | 92.8%"
    ),
    "sample_document_reference.txt": (
        "Unifile Universal AI Document\n"
        "Soniscorett Labs\n"
        "Read-Only AI Connector Telemetry and Corruption Recovery"
    )
}

for filename, content in references.items():
    with open(GT_DIR / filename, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Written {len(references)} ground-truth reference files to {GT_DIR}")
