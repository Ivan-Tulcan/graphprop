##  Synthetic Document Factory (SDF) 
Este repositorio contiene el sistema auxiliar Synthetic Document Factory (SDF).
Nota Importante: Este sistema no es el proyecto central de tesis. Es una herramienta utilitaria diseñada para generar el corpus de datos sintéticos de alta fidelidad (RFPs, anexos técnicos, normativas, historiales de proyectos) necesario para poblar e inicializar el sistema GraphRAG (Grafo de Conocimiento + RAG) que conforma el núcleo de la tesis.
##  Propósito
Los sistemas GraphRAG en el sector bancario requieren un volumen significativo de documentos interconectados para funcionar correctamente. Generar texto aleatorio con LLMs rompe la "integridad relacional" (ej. un RFP dice que el presupuesto es de $100k y su anexo dice $500k).
SDF resuelve esto utilizando una arquitectura de "Entidad Primero" (Entity-First), anclando toda la generación de texto a una base de datos semilla para garantizar que las entidades ficticias (bancos, empleados, proyectos, leyes) mantengan consistencia estricta a través de cientos de documentos generados.
##  Arquitectura del Sistema
El sistema opera en 4 capas lógicas:
Seed Database Layer (Capa Semilla): Base de datos relacional (SQLite) que actúa como la fuente de la verdad. Almacena las entidades bancarias y de proyectos base. Ningún LLM puede inventar una entidad que no exista aquí.
Schema Generation Layer (Capa Estructural): Utiliza PydanticAI y modelos de razonamiento lógico (GPT-5.2 Pro) para generar el "esqueleto" estructurado del documento en JSON (ej. definiendo el índice y restricciones de un RFP).
Prose Expansion Layer (Capa Narrativa): Un flujo de trabajo cíclico orquestado con LangGraph. Toma el esqueleto y utiliza Claude 3.7 Sonnet (en modo de pensamiento extendido) para redactar el contenido largo y técnico en Markdown. Incluye nodos de auditoría para evitar alucinaciones.
Rendering Layer (Capa de Formateo): Convierte el Markdown resultante en PDFs corporativos de alta fidelidad utilizando Pandoc y WeasyPrint, inyectando metadatos XMP (Project IDs) críticos para la posterior ingestión en Neo4j/GraphRAG.
## Stack Tecnológico (Marzo 2026)
Lenguaje: Python 3.12+  
Orquestación y Estado: langgraph  
Validación y Tipado: pydantic-ai  
Optimización de Prompts: dspy  
Integración LLM: anthropic (Claude 3.7 Sonnet), openai (GPT-5.2 Pro)  
Renderizado PDF: pandoc, weasyprint  
Base de Datos: sqlite3 / sqlalchemy  
## Requisitos Previos e Instalación
Dependencias del Sistema (OS)  
Para que el motor de renderizado de PDFs funcione, necesitas instalar las siguientes dependencias a nivel de sistema operativo:  
Ubuntu/Debian:  
sudo apt-get update  
sudo apt-get install pandoc libpango-1.0-0 libpangoft2-1.0-0  


macOS (Homebrew):  
brew install pandoc pango  


Configuración del Entorno Python  
Clona el repositorio:  
git clone [https://github.com/tu-usuario/synthetic-document-factory.git](https://github.com/tu-usuario/synthetic-document-factory.git)  
cd synthetic-document-factory  


Crea y activa un entorno virtual:  
python3.12 -m venv venv  
source venv/bin/activate  # En Windows: venv\Scripts\activate  


Instala las dependencias:  
pip install -r requirements.txt  


Configura las variables de entorno. Copia el archivo de ejemplo y añade tus API Keys:  
cp .env.example .env  

Asegúrate de incluir ANTHROPIC_API_KEY y OPENAI_API_KEY.  
##  Uso del Sistema
1. Inicializar la Base de Datos Semilla
Antes de generar documentos, debes poblar el universo ficticio:
python scripts/seed_db.py


Esto generará proyectos base (ej. PRJ-COR-001), normativas y perfiles de empleados en la base SQLite.
2. Generar Documentos mediante CLI
El sistema expone una interfaz de línea de comandos (CLI) para orquestar la generación:
Generar un RFP (Request for Proposal):
python main.py generate --doc-type RFP --project-id PRJ-COR-001


Generar Anexos Técnicos para un RFP existente:
python main.py generate --doc-type ANEXO_TECNICO --parent-doc-id DOC-RFP-001


Generación en Lote (Batch):
python main.py batch-generate --count 30 --output-dir ./output/batch_1


Los documentos resultantes se guardarán en el directorio output/ en formatos .md y .pdf (este último con etiquetas XMP incrustadas).
##  Estructura del Proyecto
synthetic-document-factory/  
├── config/                   # Configuraciones globales y prompts maestros  
├── data/    
│   ├── seed.sqlite         # Base de datos local (fuente de verdad)  
│   └── templates/          # CSS para WeasyPrint y plantillas base  
├── output/                 # PDFs y Markdowns generados  
├── scripts/  
│   └── seed_db.py          # Script de inicialización de entidades  
├── src/  
│   ├── cli/                # Interfaz de línea de comandos (main.py)  
│   ├── database/           # Modelos SQLAlchemy/Pydantic de las entidades  
│   ├── formatting/         # Pipeline de Pandoc + WeasyPrint  
│   ├── llm/                # Clientes API (Anthropic, OpenAI)  
│   └── orchestration/      # Grafos de LangGraph y lógica de agentes  
├── tests/                  # Pruebas unitarias y de integración  
├── .env.example  
├── README.md  
└── requirements.txt  


## Consideraciones de Seguridad
Dado que este sistema utiliza APIs comerciales, asegúrate de no subir el archivo .env al repositorio. Los datos generados son completamente sintéticos, por lo que no existen riesgos de exposición de PII (Información Personal Identificable) real del sector bancario.
