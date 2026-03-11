"""
Synthetic Document Factory — Streamlit Interface.

Provides a web UI for managing seed entities (banks, projects, personnel,
regulations) and browsing/filtering generated documents.

Usage:
    streamlit run app.py
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st
from sqlalchemy.orm import Session

from config.settings import settings
from src.database.models import (
    BankRow,
    PersonnelRow,
    ProjectRow,
    RegulationRow,
    get_session,
    init_db,
)
from src.database.repository import (
    get_all_banks,
    get_all_personnel,
    get_all_projects,
    get_all_regulations,
    get_bank_by_id,
    get_bank_profile,
    insert_bank,
    insert_personnel,
    insert_project,
    insert_regulation,
    upsert_bank_profile,
)
from src.models.entities import (
    BankEntity,
    BankProfile,
    EvolutionEvent,
    PersonnelEntity,
    PersonnelRole,
    ProjectEntity,
    ProjectStatus,
    RegulationEntity,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Synthetic Document Factory",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_db() -> Session:
    """Return a database session, initializing tables if needed."""
    init_db()
    return get_session()


def _delete_row(session: Session, model_class, pk_column: str, pk_value: str) -> None:
    """Delete a row by primary key."""
    row = session.query(model_class).filter(
        getattr(model_class, pk_column) == pk_value
    ).first()
    if row:
        session.delete(row)
        session.commit()


def _parse_xmp(xmp_path: Path) -> dict:
    """Parse an XMP sidecar file and return metadata dict."""
    try:
        tree = ET.parse(str(xmp_path))
        root = tree.getroot()
        ns = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "dc": "http://purl.org/dc/elements/1.1/",
            "sdf": "http://syntheticdocfactory.io/xmp/1.0/",
        }
        desc = root.find(".//rdf:Description", ns)
        if desc is None:
            return {}

        meta = {}
        # Extract attributes — they may have namespace prefixes
        for attr_key, attr_val in desc.attrib.items():
            # Strip namespace URI from key
            local_key = attr_key.split("}")[-1] if "}" in attr_key else attr_key
            meta[local_key] = attr_val

        # Extract stakeholder IDs from Bag
        bag = desc.find(".//rdf:Bag", ns)
        if bag is not None:
            meta["stakeholder_ids"] = [li.text for li in bag.findall("rdf:li", ns)]

        return meta
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# AI Profile Generation helpers
# ---------------------------------------------------------------------------

_SECTION_SCHEMAS: dict = {
    "strategy": {
        "description": "estrategia institucional",
        "instructions": "Genera misión, visión, 5-7 objetivos estratégicos y 3-5 ventajas competitivas.",
        "fields": {
            "mission": "string — declaración de misión (2-3 oraciones)",
            "vision": "string — declaración de visión a largo plazo (2-3 oraciones)",
            "strategic_objectives": "array[string] — 5-7 objetivos estratégicos concretos y medibles",
            "competitive_advantages": "array[string] — 3-5 ventajas competitivas diferenciadoras",
        },
    },
    "processes": {
        "description": "procesos de negocio",
        "instructions": "Genera listas detalladas de procesos core bancarios y procesos de soporte.",
        "fields": {
            "core_processes": "array[string] — 8-12 procesos core de negocio bancario",
            "support_processes": "array[string] — 6-10 procesos de soporte corporativo",
        },
    },
    "tech": {
        "description": "stack tecnológico",
        "instructions": "Genera el stack tecnológico completo coherente con el tamaño y país del banco.",
        "fields": {
            "core_banking_system": "string — nombre del sistema core bancario principal",
            "programming_languages": "array[string] — lenguajes de programación en uso",
            "databases": "array[string] — motores de bases de datos SQL y NoSQL",
            "cloud_providers": "array[string] — proveedores de nube (ej. AWS, Azure, GCP)",
            "devops_tools": "array[string] — herramientas CI/CD y DevOps",
            "integration_middleware": "array[string] — ESB, API gateway, mensajería",
            "security_stack": "array[string] — herramientas y frameworks de seguridad cibernética",
        },
    },
    "architecture": {
        "description": "arquitectura empresarial y tecnológica",
        "instructions": "Genera la descripción completa de la arquitectura tecnológica del banco.",
        "fields": {
            "architecture_style": "string — EXACTAMENTE uno de: Monolítica | SOA | Microservicios | Híbrida | Event-Driven | Otro",
            "architecture_layers": "array[string] — capas de la arquitectura (4-6 capas)",
            "key_systems": "array[string] — sistemas internos clave (6-10 sistemas)",
            "external_integrations": "array[string] — integraciones externas: redes de pago, reguladores, buros, etc.",
            "data_platform": "string — descripción de la plataforma de datos / data lake",
            "analytics_tools": "array[string] — herramientas de BI y analítica",
            "ai_ml_capabilities": "array[string] — capacidades AI/ML actualmente en uso",
        },
    },
    "channels": {
        "description": "canales de atención al cliente",
        "instructions": "Genera la lista de canales digitales, físicos y de terceros del banco.",
        "fields": {
            "digital_channels": "array[string] — canales digitales (app, web, chatbot, etc.)",
            "physical_channels": "array[string] — canales físicos (agencias, ATMs, kioscos, etc.)",
            "partner_channels": "array[string] — canales de terceros y aliados comerciales",
        },
    },
    "org": {
        "description": "estructura organizacional",
        "instructions": "Genera descripción de la estructura organizacional y departamentos clave.",
        "fields": {
            "org_structure_notes": "string — descripción de la estructura organizacional (3-4 párrafos)",
            "key_departments": "array[string] — 8-15 departamentos y divisiones clave",
        },
    },
    "context": {
        "description": "contexto adicional",
        "instructions": "Genera contexto rico sobre cultura, posicionamiento de mercado, desafíos y planes.",
        "fields": {
            "additional_context": "string — contexto detallado sobre el banco: cultura, mercado, desafíos actuales, iniciativas estratégicas y planes a futuro (4-6 párrafos)",
        },
    },
    "evolution": {
        "description": "historial de evolución tecnológica",
        "instructions": "Genera 6-8 hitos clave en la historia tecnológica y de negocio del banco, ordenados cronológicamente desde su fundación hasta hoy.",
        "fields": {
            "events": (
                "array[object] — cada objeto debe tener exactamente estas claves: "
                "{event_date: 'YYYY-MM-DD', "
                "category: uno de [canal, modernización, migración, servicio, adquisición, otro], "
                "title: string corto, "
                "description: string detallado (2-3 oraciones)}"
            ),
        },
    },
}


def _build_master_context(bank: "BankEntity", profile: "BankProfile") -> str:
    """Build the master context string from all known bank data for AI prompts."""
    parts = [
        f"Nombre: {bank.name}",
        f"País: {bank.country}",
        f"Clasificación: {bank.tier}",
        f"Activos totales: USD {bank.total_assets_usd} mil millones",
        f"Año de fundación: {bank.founded_year}",
    ]
    if profile.mission:
        parts.append(f"Misión: {profile.mission}")
    if profile.vision:
        parts.append(f"Visión: {profile.vision}")
    if profile.strategic_objectives:
        parts.append(f"Objetivos: {'; '.join(profile.strategic_objectives[:4])}")
    if profile.core_banking_system:
        parts.append(f"Core bancario: {profile.core_banking_system}")
    if profile.architecture_style:
        parts.append(f"Arquitectura: {profile.architecture_style}")
    if profile.cloud_providers:
        parts.append(f"Cloud: {', '.join(profile.cloud_providers)}")
    if profile.digital_channels:
        parts.append(f"Canales digitales: {', '.join(profile.digital_channels[:4])}")
    if profile.core_processes:
        parts.append(f"Procesos core: {', '.join(profile.core_processes[:5])}")
    if profile.key_departments:
        parts.append(f"Departamentos: {', '.join(profile.key_departments[:5])}")
    if profile.evolution_history:
        last = profile.evolution_history[-1]
        parts.append(f"Último hito registrado ({last.event_date}): {last.title}")
    return "\n".join(parts)


def _ai_generate_section(bank: "BankEntity", profile: "BankProfile", section: str) -> dict:
    """Call gpt-4o-mini to generate structured content for one profile section."""
    from openai import OpenAI

    schema = _SECTION_SCHEMAS[section]
    fields_desc = "\n".join(f"  - {k}: {v}" for k, v in schema["fields"].items())
    master_ctx = _build_master_context(bank, profile)

    system_msg = (
        "Eres un consultor senior especializado en banca y transformación digital. "
        "Genera información realista, específica y coherente para el perfil institucional "
        "de un banco ficticio. Responde ÚNICAMENTE con un objeto JSON válido. "
        "Todo el contenido debe estar en ESPAÑOL."
    )
    user_msg = (
        f"Genera la sección '{schema['description']}' para el banco '{bank.name}'.\n\n"
        f"CONTEXTO CONOCIDO DEL BANCO:\n{master_ctx}\n\n"
        f"INSTRUCCIÓN: {schema['instructions']}\n\n"
        f"RESPONDE CON EXACTAMENTE ESTE ESQUEMA JSON:\n{{\n{fields_desc}\n}}\n\n"
        "El contenido debe ser específico, realista y coherente con todos los datos conocidos. "
        "Devuelve ÚNICAMENTE el objeto JSON válido, sin explicaciones adicionales."
    )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return json.loads(resp.choices[0].message.content)


# ---------------------------------------------------------------------------
# Document type metadata (shared between generation page and viewer)
# ---------------------------------------------------------------------------

_DOC_TYPE_META: dict[str, tuple[str, str, str]] = {
    # key: (icon, label, description)
    "rfp": (
        "📝",
        "RFP Principal",
        "Solicitud de Propuestas principal del proyecto, incluyendo alcance, requisitos técnicos, "
        "criterios de evaluación y condiciones contractuales.",
    ),
    "technical_annex": (
        "📎",
        "Anexo Técnico",
        "Especificaciones técnicas detalladas, requisitos de integración, criterios de aceptación "
        "y notas de arquitectura que complementan el RFP.",
    ),
    "meeting_minutes": (
        "📋",
        "Actas de Reunión",
        "Minuta de la reunión de kickoff u otras sesiones del proyecto, con agenda, "
        "acuerdos y compromisos adquiridos.",
    ),
    "rfp_qa": (
        "❓",
        "Preguntas y Respuestas de RFP",
        "Tabla Q&A donde proveedores concursantes formularon preguntas sobre el RFP "
        "y el banco proporcionó respuestas oficiales.",
    ),
    "project_history": (
        "📊",
        "Historial del Proyecto",
        "Documentación histórica y de estado del proyecto, incluyendo fases, contribuciones "
        "de stakeholders, riesgos y lecciones aprendidas.",
    ),
}


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.title("🏦 SDF Admin")
page = st.sidebar.radio(
    "Navegación",
    [
        "🏢 Bancos",
        "📊 Fuente de la Verdad",
        "📁 Proyectos",
        "👥 Personal",
        "📜 Regulaciones",
        "🚀 Generar Documentos",
        "📄 Documentos Generados",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: BANCOS
# ═══════════════════════════════════════════════════════════════════════════

if page == "🏢 Bancos":
    st.header("🏢 Gestión de Bancos")
    session = _get_db()

    try:
        banks = get_all_banks(session)

        # ---- Table view ----
        if banks:
            st.subheader("Bancos registrados")
            bank_data = [
                {
                    "ID": b.bank_id,
                    "Nombre": b.name,
                    "País": b.country,
                    "Tier": b.tier,
                    "Activos (USD B)": b.total_assets_usd,
                    "Fundado": b.founded_year,
                }
                for b in banks
            ]
            st.dataframe(bank_data, use_container_width=True, hide_index=True)
        else:
            st.info("No hay bancos registrados. Agrega uno abajo o ejecuta el seeder.")

        # ---- Add / Edit ----
        st.subheader("Agregar / Editar Banco")

        existing_ids = [b.bank_id for b in banks]
        edit_mode = st.toggle("Modo edición (seleccionar banco existente)", key="bank_edit_toggle")

        if edit_mode and banks:
            selected_id = st.selectbox("Seleccionar banco", existing_ids, key="bank_select")
            selected = next(b for b in banks if b.bank_id == selected_id)
            default_id = selected.bank_id
            default_name = selected.name
            default_country = selected.country
            default_tier = selected.tier
            default_assets = selected.total_assets_usd
            default_year = selected.founded_year
            id_disabled = True
        else:
            # Suggest next ID
            existing_nums = [int(b.bank_id.split("-")[1]) for b in banks if "-" in b.bank_id]
            next_num = max(existing_nums, default=0) + 1
            default_id = f"BNK-{next_num:03d}"
            default_name = ""
            default_country = "Ecuador"
            default_tier = "Tier 1"
            default_assets = 0.0
            default_year = 2000
            id_disabled = False

        with st.form("bank_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                bank_id = st.text_input("ID del Banco", value=default_id, disabled=id_disabled)
                name = st.text_input("Nombre", value=default_name)
                country = st.text_input("País", value=default_country)
            with col2:
                tier = st.selectbox("Tier", ["Tier 1", "Tier 2", "Tier 3"], index=["Tier 1", "Tier 2", "Tier 3"].index(default_tier) if default_tier in ["Tier 1", "Tier 2", "Tier 3"] else 0)
                total_assets = st.number_input("Activos Totales (USD Billions)", value=default_assets, min_value=0.0, step=0.1)
                founded_year = st.number_input("Año de Fundación", value=default_year, min_value=1800, max_value=2030, step=1)

            submitted = st.form_submit_button("💾 Guardar Banco")
            if submitted:
                if not bank_id or not name:
                    st.error("ID y Nombre son obligatorios.")
                else:
                    entity = BankEntity(
                        bank_id=bank_id,
                        name=name,
                        country=country,
                        tier=tier,
                        total_assets_usd=total_assets,
                        founded_year=int(founded_year),
                    )
                    insert_bank(session, entity)
                    session.commit()
                    st.success(f"Banco '{name}' guardado correctamente.")
                    st.rerun()

        # ---- Delete ----
        if banks:
            st.subheader("Eliminar Banco")
            del_id = st.selectbox("Seleccionar banco a eliminar", existing_ids, key="bank_del")
            if st.button("🗑️ Eliminar Banco", type="secondary"):
                _delete_row(session, BankRow, "bank_id", del_id)
                st.success(f"Banco '{del_id}' eliminado.")
                st.rerun()
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════# PAGE: FUENTE DE LA VERDAD
# ═══════════════════════════════════════════════════════════════════════

elif page == "📊 Fuente de la Verdad":
    st.header("📊 Fuente de la Verdad — Perfil Institucional")
    session = _get_db()

    try:
        banks = get_all_banks(session)

        if not banks:
            st.warning("No hay bancos registrados. Primero crea un banco en la pestaña Bancos.")
        else:
            bank_map = {b.bank_id: b.name for b in banks}
            selected_bank = st.selectbox(
                "Seleccionar Banco",
                options=[b.bank_id for b in banks],
                format_func=lambda x: f"{bank_map[x]} ({x})",
                key="profile_bank_select",
            )
            bank_entity = next(b for b in banks if b.bank_id == selected_bank)

            # Load existing profile or create empty
            profile = get_bank_profile(session, selected_bank)
            if profile is None:
                profile = BankProfile(bank_id=selected_bank)
                st.info("Este banco aún no tiene perfil. Completa los campos y guarda.")

            # ── Sidebar: Generate full profile ──────────────────────────
            st.sidebar.divider()
            st.sidebar.markdown("### 🤖 Asistente IA")
            if st.sidebar.button(
                "🤖 Generar Perfil Completo con IA",
                key=f"ai_full_{selected_bank}",
                type="primary",
                help="Genera todas las secciones del perfil en un solo clic usando gpt-4o-mini.",
            ):
                _sections_all = ["strategy", "processes", "tech", "architecture", "channels", "org", "context"]
                _prog = st.sidebar.progress(0, text="Iniciando generación...")
                for _i, _sec in enumerate(_sections_all):
                    _prog.progress(
                        int((_i / len(_sections_all)) * 100),
                        text=f"Generando {_SECTION_SCHEMAS[_sec]['description']}...",
                    )
                    try:
                        _res = _ai_generate_section(bank_entity, profile, _sec)
                        st.session_state[f"ai_{selected_bank}_{_sec}"] = _res
                    except Exception as _exc:
                        st.sidebar.warning(f"[{_sec}] Error: {_exc}")
                _prog.progress(100, text="¡Completo!")
                st.rerun()

            # ── TABS ─────────────────────────────────────────────────────
            tab_strategy, tab_processes, tab_tech, tab_arch, tab_channels, tab_org, tab_history, tab_extra, tab_json = st.tabs([
                "🎯 Estrategia",
                "⚙️ Procesos",
                "💻 Tecnología",
                "🏗️ Arquitectura",
                "📡 Canales",
                "🏢 Organización",
                "📈 Evolución",
                "📝 Contexto Adicional",
                "🔧 JSON Completo",
            ])

            # ── TAB: Estrategia ──────────────────────────────────────────
            with tab_strategy:
                st.subheader("🎯 Estrategia y Visión")
                if st.button(
                    "🤖 Generar Estrategia con IA",
                    key=f"ai_btn_strategy_{selected_bank}",
                    help="Genera misión, visión, objetivos y ventajas competitivas usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando estrategia institucional..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "strategy")
                            st.session_state[f"wgt_{selected_bank}_mission"] = _r.get("mission", "")
                            st.session_state[f"wgt_{selected_bank}_vision"] = _r.get("vision", "")
                            st.session_state[f"wgt_{selected_bank}_objectives"] = "\n".join(_r.get("strategic_objectives", []))
                            st.session_state[f"wgt_{selected_bank}_advantages"] = "\n".join(_r.get("competitive_advantages", []))
                            st.session_state.pop(f"ai_{selected_bank}_strategy", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                # Absorb full-profile AI results into widget state
                _ai_strategy = st.session_state.pop(f"ai_{selected_bank}_strategy", None)
                if _ai_strategy:
                    st.session_state[f"wgt_{selected_bank}_mission"] = _ai_strategy.get("mission", "")
                    st.session_state[f"wgt_{selected_bank}_vision"] = _ai_strategy.get("vision", "")
                    st.session_state[f"wgt_{selected_bank}_objectives"] = "\n".join(_ai_strategy.get("strategic_objectives", []))
                    st.session_state[f"wgt_{selected_bank}_advantages"] = "\n".join(_ai_strategy.get("competitive_advantages", []))
                    st.rerun()
                with st.form(f"profile_strategy_{selected_bank}", clear_on_submit=False):
                    p_mission = st.text_area(
                        "Misión",
                        value=profile.mission,
                        key=f"wgt_{selected_bank}_mission",
                        height=80,
                    )
                    p_vision = st.text_area(
                        "Visión",
                        value=profile.vision,
                        key=f"wgt_{selected_bank}_vision",
                        height=80,
                    )
                    p_objectives = st.text_area(
                        "Objetivos Estratégicos (uno por línea)",
                        value="\n".join(profile.strategic_objectives),
                        key=f"wgt_{selected_bank}_objectives",
                        height=120,
                    )
                    p_advantages = st.text_area(
                        "Ventajas Competitivas (una por línea)",
                        value="\n".join(profile.competitive_advantages),
                        key=f"wgt_{selected_bank}_advantages",
                        height=100,
                    )
                    if st.form_submit_button("💾 Guardar Estrategia"):
                        profile.mission = p_mission
                        profile.vision = p_vision
                        profile.strategic_objectives = [x.strip() for x in p_objectives.strip().splitlines() if x.strip()]
                        profile.competitive_advantages = [x.strip() for x in p_advantages.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Estrategia guardada.")
                        st.rerun()

            # ── TAB: Procesos ────────────────────────────────────────────
            with tab_processes:
                st.subheader("⚙️ Procesos de Negocio")
                if st.button(
                    "🤖 Generar Procesos con IA",
                    key=f"ai_btn_processes_{selected_bank}",
                    help="Genera listas de procesos core y de soporte usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando procesos de negocio..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "processes")
                            st.session_state[f"wgt_{selected_bank}_core_procs"] = "\n".join(_r.get("core_processes", []))
                            st.session_state[f"wgt_{selected_bank}_support_procs"] = "\n".join(_r.get("support_processes", []))
                            st.session_state.pop(f"ai_{selected_bank}_processes", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                _ai_proc = st.session_state.pop(f"ai_{selected_bank}_processes", None)
                if _ai_proc:
                    st.session_state[f"wgt_{selected_bank}_core_procs"] = "\n".join(_ai_proc.get("core_processes", []))
                    st.session_state[f"wgt_{selected_bank}_support_procs"] = "\n".join(_ai_proc.get("support_processes", []))
                    st.rerun()
                with st.form(f"profile_processes_{selected_bank}", clear_on_submit=False):
                    p_core = st.text_area(
                        "Procesos Core (uno por línea)",
                        value="\n".join(profile.core_processes),
                        key=f"wgt_{selected_bank}_core_procs",
                        height=120,
                        help="Ej: Captaciones, Colocaciones, Pagos, Comercio Exterior, Tesorería",
                    )
                    p_support = st.text_area(
                        "Procesos de Soporte (uno por línea)",
                        value="\n".join(profile.support_processes),
                        key=f"wgt_{selected_bank}_support_procs",
                        height=120,
                        help="Ej: Recursos Humanos, Legal, Compliance, Auditoría Interna",
                    )
                    if st.form_submit_button("💾 Guardar Procesos"):
                        profile.core_processes = [x.strip() for x in p_core.strip().splitlines() if x.strip()]
                        profile.support_processes = [x.strip() for x in p_support.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Procesos guardados.")
                        st.rerun()

            # ── TAB: Tecnología ──────────────────────────────────────────
            with tab_tech:
                st.subheader("💻 Stack Tecnológico")
                if st.button(
                    "🤖 Generar Stack Tecnológico con IA",
                    key=f"ai_btn_tech_{selected_bank}",
                    help="Genera el stack tecnológico completo usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando stack tecnológico..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "tech")
                            st.session_state[f"wgt_{selected_bank}_core_sys"] = _r.get("core_banking_system", "")
                            st.session_state[f"wgt_{selected_bank}_langs"] = "\n".join(_r.get("programming_languages", []))
                            st.session_state[f"wgt_{selected_bank}_dbs"] = "\n".join(_r.get("databases", []))
                            st.session_state[f"wgt_{selected_bank}_cloud"] = "\n".join(_r.get("cloud_providers", []))
                            st.session_state[f"wgt_{selected_bank}_devops"] = "\n".join(_r.get("devops_tools", []))
                            st.session_state[f"wgt_{selected_bank}_middleware"] = "\n".join(_r.get("integration_middleware", []))
                            st.session_state[f"wgt_{selected_bank}_security"] = "\n".join(_r.get("security_stack", []))
                            st.session_state.pop(f"ai_{selected_bank}_tech", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                _ai_tech = st.session_state.pop(f"ai_{selected_bank}_tech", None)
                if _ai_tech:
                    st.session_state[f"wgt_{selected_bank}_core_sys"] = _ai_tech.get("core_banking_system", "")
                    st.session_state[f"wgt_{selected_bank}_langs"] = "\n".join(_ai_tech.get("programming_languages", []))
                    st.session_state[f"wgt_{selected_bank}_dbs"] = "\n".join(_ai_tech.get("databases", []))
                    st.session_state[f"wgt_{selected_bank}_cloud"] = "\n".join(_ai_tech.get("cloud_providers", []))
                    st.session_state[f"wgt_{selected_bank}_devops"] = "\n".join(_ai_tech.get("devops_tools", []))
                    st.session_state[f"wgt_{selected_bank}_middleware"] = "\n".join(_ai_tech.get("integration_middleware", []))
                    st.session_state[f"wgt_{selected_bank}_security"] = "\n".join(_ai_tech.get("security_stack", []))
                    st.rerun()
                with st.form(f"profile_tech_{selected_bank}", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        p_core_sys = st.text_input(
                            "Core Bancario",
                            value=profile.core_banking_system,
                            key=f"wgt_{selected_bank}_core_sys",
                            help="Ej: Temenos T24, Finacle, Cobis, Mambu",
                        )
                        p_langs = st.text_area(
                            "Lenguajes de Programación (uno por línea)",
                            value="\n".join(profile.programming_languages),
                            key=f"wgt_{selected_bank}_langs",
                            height=80,
                        )
                        p_dbs = st.text_area(
                            "Bases de Datos (una por línea)",
                            value="\n".join(profile.databases),
                            key=f"wgt_{selected_bank}_dbs",
                            height=80,
                        )
                        p_cloud = st.text_area(
                            "Proveedores Cloud (uno por línea)",
                            value="\n".join(profile.cloud_providers),
                            key=f"wgt_{selected_bank}_cloud",
                            height=60,
                        )
                    with col2:
                        p_devops = st.text_area(
                            "Herramientas DevOps (una por línea)",
                            value="\n".join(profile.devops_tools),
                            key=f"wgt_{selected_bank}_devops",
                            height=80,
                        )
                        p_integration = st.text_area(
                            "Middleware/Integración (uno por línea)",
                            value="\n".join(profile.integration_middleware),
                            key=f"wgt_{selected_bank}_middleware",
                            height=80,
                        )
                        p_security = st.text_area(
                            "Stack de Seguridad (uno por línea)",
                            value="\n".join(profile.security_stack),
                            key=f"wgt_{selected_bank}_security",
                            height=80,
                        )
                    if st.form_submit_button("💾 Guardar Tecnología"):
                        profile.core_banking_system = p_core_sys
                        profile.programming_languages = [x.strip() for x in p_langs.strip().splitlines() if x.strip()]
                        profile.databases = [x.strip() for x in p_dbs.strip().splitlines() if x.strip()]
                        profile.cloud_providers = [x.strip() for x in p_cloud.strip().splitlines() if x.strip()]
                        profile.devops_tools = [x.strip() for x in p_devops.strip().splitlines() if x.strip()]
                        profile.integration_middleware = [x.strip() for x in p_integration.strip().splitlines() if x.strip()]
                        profile.security_stack = [x.strip() for x in p_security.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Stack tecnológico guardado.")
                        st.rerun()

            # ── TAB: Arquitectura ────────────────────────────────────────
            with tab_arch:
                st.subheader("🏗️ Arquitectura Empresarial y Tecnológica")
                _arch_opts = ["Monolítica", "SOA", "Microservicios", "Híbrida", "Event-Driven", "Otro"]
                if st.button(
                    "🤖 Generar Arquitectura con IA",
                    key=f"ai_btn_arch_{selected_bank}",
                    help="Genera la descripción de arquitectura tecnológica usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando arquitectura..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "architecture")
                            _style = _r.get("architecture_style", "Híbrida")
                            st.session_state[f"wgt_{selected_bank}_arch_style"] = _style if _style in _arch_opts else "Híbrida"
                            st.session_state[f"wgt_{selected_bank}_arch_layers"] = "\n".join(_r.get("architecture_layers", []))
                            st.session_state[f"wgt_{selected_bank}_key_systems"] = "\n".join(_r.get("key_systems", []))
                            st.session_state[f"wgt_{selected_bank}_ext_int"] = "\n".join(_r.get("external_integrations", []))
                            st.session_state[f"wgt_{selected_bank}_data_plat"] = _r.get("data_platform", "")
                            st.session_state[f"wgt_{selected_bank}_analytics"] = "\n".join(_r.get("analytics_tools", []))
                            st.session_state[f"wgt_{selected_bank}_ai_ml"] = "\n".join(_r.get("ai_ml_capabilities", []))
                            st.session_state.pop(f"ai_{selected_bank}_architecture", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                _ai_arch = st.session_state.pop(f"ai_{selected_bank}_architecture", None)
                if _ai_arch:
                    _style = _ai_arch.get("architecture_style", "Híbrida")
                    st.session_state[f"wgt_{selected_bank}_arch_style"] = _style if _style in _arch_opts else "Híbrida"
                    st.session_state[f"wgt_{selected_bank}_arch_layers"] = "\n".join(_ai_arch.get("architecture_layers", []))
                    st.session_state[f"wgt_{selected_bank}_key_systems"] = "\n".join(_ai_arch.get("key_systems", []))
                    st.session_state[f"wgt_{selected_bank}_ext_int"] = "\n".join(_ai_arch.get("external_integrations", []))
                    st.session_state[f"wgt_{selected_bank}_data_plat"] = _ai_arch.get("data_platform", "")
                    st.session_state[f"wgt_{selected_bank}_analytics"] = "\n".join(_ai_arch.get("analytics_tools", []))
                    st.session_state[f"wgt_{selected_bank}_ai_ml"] = "\n".join(_ai_arch.get("ai_ml_capabilities", []))
                    st.rerun()
                with st.form(f"profile_arch_{selected_bank}", clear_on_submit=False):
                    _cur_arch = profile.architecture_style
                    _arch_idx = _arch_opts.index(_cur_arch) if _cur_arch in _arch_opts else 0
                    p_arch_style = st.selectbox(
                        "Estilo de Arquitectura",
                        _arch_opts,
                        index=_arch_idx,
                        key=f"wgt_{selected_bank}_arch_style",
                    )
                    p_arch_layers = st.text_area(
                        "Capas de Arquitectura (una por línea)",
                        value="\n".join(profile.architecture_layers),
                        key=f"wgt_{selected_bank}_arch_layers",
                        height=100,
                        help="Ej: Capa de Presentación, Capa de Servicios, Capa de Negocio, Capa de Datos",
                    )
                    p_key_systems = st.text_area(
                        "Sistemas Clave (uno por línea)",
                        value="\n".join(profile.key_systems),
                        key=f"wgt_{selected_bank}_key_systems",
                        height=100,
                        help="Ej: Core Bancario, CRM, ERP, Data Warehouse, Motor de Riesgos",
                    )
                    p_ext_int = st.text_area(
                        "Integraciones Externas (una por línea)",
                        value="\n".join(profile.external_integrations),
                        key=f"wgt_{selected_bank}_ext_int",
                        height=80,
                        help="Ej: SWIFT, Visa/Mastercard, Buró de Crédito, Regulador",
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        p_data_plat = st.text_area(
                            "Plataforma de Datos",
                            value=profile.data_platform,
                            key=f"wgt_{selected_bank}_data_plat",
                            height=60,
                        )
                    with col2:
                        p_analytics = st.text_area(
                            "Herramientas de Analítica (una por línea)",
                            value="\n".join(profile.analytics_tools),
                            key=f"wgt_{selected_bank}_analytics",
                            height=60,
                        )
                    p_ai = st.text_area(
                        "Capacidades AI/ML (una por línea)",
                        value="\n".join(profile.ai_ml_capabilities),
                        key=f"wgt_{selected_bank}_ai_ml",
                        height=60,
                    )
                    if st.form_submit_button("💾 Guardar Arquitectura"):
                        profile.architecture_style = p_arch_style
                        profile.architecture_layers = [x.strip() for x in p_arch_layers.strip().splitlines() if x.strip()]
                        profile.key_systems = [x.strip() for x in p_key_systems.strip().splitlines() if x.strip()]
                        profile.external_integrations = [x.strip() for x in p_ext_int.strip().splitlines() if x.strip()]
                        profile.data_platform = p_data_plat
                        profile.analytics_tools = [x.strip() for x in p_analytics.strip().splitlines() if x.strip()]
                        profile.ai_ml_capabilities = [x.strip() for x in p_ai.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Arquitectura guardada.")
                        st.rerun()

            # ── TAB: Canales ─────────────────────────────────────────────
            with tab_channels:
                st.subheader("📡 Canales de Atención")
                if st.button(
                    "🤖 Generar Canales con IA",
                    key=f"ai_btn_channels_{selected_bank}",
                    help="Genera la lista de canales digitales, físicos y de terceros usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando canales..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "channels")
                            st.session_state[f"wgt_{selected_bank}_digital_ch"] = "\n".join(_r.get("digital_channels", []))
                            st.session_state[f"wgt_{selected_bank}_physical_ch"] = "\n".join(_r.get("physical_channels", []))
                            st.session_state[f"wgt_{selected_bank}_partner_ch"] = "\n".join(_r.get("partner_channels", []))
                            st.session_state.pop(f"ai_{selected_bank}_channels", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                _ai_ch = st.session_state.pop(f"ai_{selected_bank}_channels", None)
                if _ai_ch:
                    st.session_state[f"wgt_{selected_bank}_digital_ch"] = "\n".join(_ai_ch.get("digital_channels", []))
                    st.session_state[f"wgt_{selected_bank}_physical_ch"] = "\n".join(_ai_ch.get("physical_channels", []))
                    st.session_state[f"wgt_{selected_bank}_partner_ch"] = "\n".join(_ai_ch.get("partner_channels", []))
                    st.rerun()
                with st.form(f"profile_channels_{selected_bank}", clear_on_submit=False):
                    p_digital = st.text_area(
                        "Canales Digitales (uno por línea)",
                        value="\n".join(profile.digital_channels),
                        key=f"wgt_{selected_bank}_digital_ch",
                        height=80,
                        help="Ej: App Móvil iOS, App Móvil Android, Banca Web, Chatbot, WhatsApp Banking",
                    )
                    p_physical = st.text_area(
                        "Canales Físicos (uno por línea)",
                        value="\n".join(profile.physical_channels),
                        key=f"wgt_{selected_bank}_physical_ch",
                        height=80,
                        help="Ej: Agencias, Cajeros ATM, Kioscos, Corresponsales bancarios",
                    )
                    p_partner = st.text_area(
                        "Canales de Terceros/Partners (uno por línea)",
                        value="\n".join(profile.partner_channels),
                        key=f"wgt_{selected_bank}_partner_ch",
                        height=60,
                    )
                    if st.form_submit_button("💾 Guardar Canales"):
                        profile.digital_channels = [x.strip() for x in p_digital.strip().splitlines() if x.strip()]
                        profile.physical_channels = [x.strip() for x in p_physical.strip().splitlines() if x.strip()]
                        profile.partner_channels = [x.strip() for x in p_partner.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Canales guardados.")
                        st.rerun()

            # ── TAB: Organización ────────────────────────────────────────
            with tab_org:
                st.subheader("🏢 Estructura Organizacional")
                if st.button(
                    "🤖 Generar Organización con IA",
                    key=f"ai_btn_org_{selected_bank}",
                    help="Genera la estructura organizacional y departamentos usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando estructura organizacional..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "org")
                            st.session_state[f"wgt_{selected_bank}_org_notes"] = _r.get("org_structure_notes", "")
                            st.session_state[f"wgt_{selected_bank}_depts"] = "\n".join(_r.get("key_departments", []))
                            st.session_state.pop(f"ai_{selected_bank}_org", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                _ai_org = st.session_state.pop(f"ai_{selected_bank}_org", None)
                if _ai_org:
                    st.session_state[f"wgt_{selected_bank}_org_notes"] = _ai_org.get("org_structure_notes", "")
                    st.session_state[f"wgt_{selected_bank}_depts"] = "\n".join(_ai_org.get("key_departments", []))
                    st.rerun()
                with st.form(f"profile_org_{selected_bank}", clear_on_submit=False):
                    p_org_notes = st.text_area(
                        "Notas sobre Estructura Organizacional",
                        value=profile.org_structure_notes,
                        key=f"wgt_{selected_bank}_org_notes",
                        height=120,
                    )
                    p_depts = st.text_area(
                        "Departamentos Clave (uno por línea)",
                        value="\n".join(profile.key_departments),
                        key=f"wgt_{selected_bank}_depts",
                        height=100,
                    )
                    if st.form_submit_button("💾 Guardar Organización"):
                        profile.org_structure_notes = p_org_notes
                        profile.key_departments = [x.strip() for x in p_depts.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Organización guardada.")
                        st.rerun()

            # ── TAB: Evolución ───────────────────────────────────────────
            with tab_history:
                st.subheader("📈 Historial de Evolución Tecnológica y de Negocio")
                st.caption(
                    "Registra hitos importantes: migraciones de core, apertura de canales, "
                    "modernizaciones, adquisiciones, nuevos servicios, etc."
                )

                # AI: Suggest events to add
                if st.button(
                    "🤖 Sugerir Eventos con IA",
                    key=f"ai_btn_evo_{selected_bank}",
                    help="La IA sugiere hitos históricos. Puedes añadir los que desees al historial.",
                ):
                    with st.spinner("Generando sugerencias de hitos históricos..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "evolution")
                            st.session_state[f"ai_{selected_bank}_evo_suggestions"] = _r.get("events", [])
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")

                # Show AI-suggested events (if any)
                _evo_suggestions = st.session_state.get(f"ai_{selected_bank}_evo_suggestions", [])
                if _evo_suggestions:
                    st.markdown("#### 💡 Sugerencias de la IA — selecciona los que quieras agregar:")
                    _cat_icons = {
                        "canal": "📡", "modernización": "🚀", "migración": "🔄",
                        "servicio": "➕", "adquisición": "🤝", "otro": "📌",
                    }
                    for _si, _evt in enumerate(_evo_suggestions):
                        _icon = _cat_icons.get(_evt.get("category", "otro"), "📌")
                        with st.expander(f"{_icon} {_evt.get('event_date', '?')} — {_evt.get('title', '?')}"):
                            st.markdown(f"**Categoría:** {_evt.get('category', '?')}")
                            st.markdown(f"**Descripción:** {_evt.get('description', '')}")
                            if st.button(f"➕ Agregar al historial", key=f"add_evo_{selected_bank}_{_si}"):
                                try:
                                    new_evt = EvolutionEvent(
                                        event_date=_evt["event_date"],
                                        category=_evt.get("category", "otro"),
                                        title=_evt.get("title", ""),
                                        description=_evt.get("description", ""),
                                    )
                                    profile.evolution_history.append(new_evt)
                                    profile.evolution_history.sort(key=lambda e: e.event_date)
                                    upsert_bank_profile(session, profile)
                                    session.commit()
                                    # Remove this suggestion
                                    st.session_state[f"ai_{selected_bank}_evo_suggestions"].pop(_si)
                                    st.rerun()
                                except Exception as _e:
                                    st.error(f"Error al agregar evento: {_e}")
                    if st.button("✖ Descartar sugerencias", key=f"discard_evo_{selected_bank}"):
                        del st.session_state[f"ai_{selected_bank}_evo_suggestions"]
                        st.rerun()
                    st.markdown("---")

                # Show existing events
                if profile.evolution_history:
                    for idx, evt in enumerate(profile.evolution_history):
                        _cat_icons2 = {
                            "canal": "📡", "modernización": "🚀", "migración": "🔄",
                            "servicio": "➕", "adquisición": "🤝", "otro": "📌",
                        }
                        icon = _cat_icons2.get(evt.category, "📌")
                        with st.expander(f"{icon} {evt.event_date} — {evt.title}"):
                            st.markdown(f"**Categoría:** {evt.category}")
                            st.markdown(f"**Descripción:** {evt.description}")
                            if st.button("❌ Eliminar evento", key=f"del_evt_{selected_bank}_{idx}"):
                                profile.evolution_history.pop(idx)
                                upsert_bank_profile(session, profile)
                                session.commit()
                                st.rerun()
                else:
                    st.info("No hay eventos registrados aún.")

                # Add new event manually
                st.markdown("---")
                st.markdown("**Agregar Nuevo Evento Manualmente**")
                with st.form(f"add_event_{selected_bank}", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        evt_date = st.date_input("Fecha del Evento", value=date.today())
                        evt_category = st.selectbox(
                            "Categoría",
                            ["canal", "modernización", "migración", "servicio", "adquisición", "otro"],
                        )
                    with col2:
                        evt_title = st.text_input("Título del Evento")
                    evt_desc = st.text_area("Descripción", height=80)
                    if st.form_submit_button("➕ Agregar Evento"):
                        if not evt_title:
                            st.error("El título es obligatorio.")
                        else:
                            new_event = EvolutionEvent(
                                event_date=evt_date,
                                category=evt_category,
                                title=evt_title,
                                description=evt_desc,
                            )
                            profile.evolution_history.append(new_event)
                            profile.evolution_history.sort(key=lambda e: e.event_date)
                            upsert_bank_profile(session, profile)
                            session.commit()
                            st.success(f"Evento '{evt_title}' agregado.")
                            st.rerun()

            # ── TAB: Contexto Adicional ──────────────────────────────────
            with tab_extra:
                st.subheader("📝 Contexto Adicional")
                if st.button(
                    "🤖 Generar Contexto con IA",
                    key=f"ai_btn_context_{selected_bank}",
                    help="Genera contexto rico sobre cultura, mercado y desafíos del banco usando gpt-4o-mini.",
                ):
                    with st.spinner("Generando contexto adicional..."):
                        try:
                            _r = _ai_generate_section(bank_entity, profile, "context")
                            st.session_state[f"wgt_{selected_bank}_extra"] = _r.get("additional_context", "")
                            st.session_state.pop(f"ai_{selected_bank}_context", None)
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Error IA: {_e}")
                _ai_ctx = st.session_state.pop(f"ai_{selected_bank}_context", None)
                if _ai_ctx:
                    st.session_state[f"wgt_{selected_bank}_extra"] = _ai_ctx.get("additional_context", "")
                    st.rerun()
                with st.form(f"profile_extra_{selected_bank}", clear_on_submit=False):
                    p_extra = st.text_area(
                        "Notas adicionales (texto libre)",
                        value=profile.additional_context,
                        key=f"wgt_{selected_bank}_extra",
                        height=220,
                        help="Cultura corporativa, posicionamiento de mercado, desafíos, regulaciones específicas, planes de transformación digital, etc.",
                    )
                    if st.form_submit_button("💾 Guardar Contexto"):
                        profile.additional_context = p_extra
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Contexto adicional guardado.")
                        st.rerun()

            # ── TAB: JSON Completo ───────────────────────────────────────
            with tab_json:
                st.subheader("🔧 Perfil JSON Completo")
                st.caption("Vista del perfil completo en formato JSON. Puedes editarlo directamente.")
                profile_json_str = json.dumps(
                    profile.model_dump(mode="json"),
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
                edited_json = st.text_area(
                    "JSON del Perfil",
                    value=profile_json_str,
                    height=500,
                    key=f"profile_json_editor_{selected_bank}",
                )
                if st.button("💾 Guardar JSON Editado"):
                    try:
                        parsed = json.loads(edited_json)
                        parsed["bank_id"] = selected_bank  # Ensure bank_id consistency
                        updated_profile = BankProfile.model_validate(parsed)
                        upsert_bank_profile(session, updated_profile)
                        session.commit()
                        st.success("Perfil actualizado desde JSON.")
                        st.rerun()
                    except (json.JSONDecodeError, Exception) as e:
                        st.error(f"JSON inválido: {e}")
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════# PAGE: PROYECTOS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📁 Proyectos":
    st.header("📁 Gestión de Proyectos")
    session = _get_db()

    try:
        projects = get_all_projects(session)
        banks = get_all_banks(session)
        personnel = get_all_personnel(session)

        bank_map = {b.bank_id: b.name for b in banks}
        personnel_map = {p.personnel_id: f"{p.full_name} ({p.role.value})" for p in personnel}

        # ---- Table view ----
        if projects:
            st.subheader("Proyectos registrados")
            proj_data = [
                {
                    "ID": p.project_id,
                    "Nombre": p.name,
                    "Banco": bank_map.get(p.bank_id, p.bank_id),
                    "Estado": p.status.value,
                    "Presupuesto (USD)": f"${p.budget_usd:,.2f}",
                    "Inicio": str(p.start_date),
                    "Fin": str(p.end_date or "—"),
                    "Stakeholders": len(p.stakeholder_ids),
                }
                for p in projects
            ]
            st.dataframe(proj_data, use_container_width=True, hide_index=True)
        else:
            st.info("No hay proyectos registrados.")

        # ---- Add / Edit ----
        st.subheader("Agregar / Editar Proyecto")

        existing_ids = [p.project_id for p in projects]
        edit_mode = st.toggle("Modo edición", key="proj_edit_toggle")

        if edit_mode and projects:
            selected_id = st.selectbox("Seleccionar proyecto", existing_ids, key="proj_select")
            sel = next(p for p in projects if p.project_id == selected_id)
            d_id = sel.project_id
            d_bank = sel.bank_id
            d_name = sel.name
            d_desc = sel.description
            d_status = sel.status.value
            d_budget = sel.budget_usd
            d_start = sel.start_date
            d_end = sel.end_date
            d_stakeholders = sel.stakeholder_ids
            id_disabled = True
        else:
            existing_nums = [int(p.project_id.split("-")[1]) for p in projects if "-" in p.project_id]
            next_num = max(existing_nums, default=0) + 1
            d_id = f"PRJ-{next_num:03d}"
            d_bank = banks[0].bank_id if banks else ""
            d_name = ""
            d_desc = ""
            d_status = "planning"
            d_budget = 0.0
            d_start = date.today()
            d_end = None
            d_stakeholders = []
            id_disabled = False

        bank_ids = [b.bank_id for b in banks]
        status_options = [s.value for s in ProjectStatus]

        with st.form("project_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                proj_id = st.text_input("ID del Proyecto", value=d_id, disabled=id_disabled)
                proj_name = st.text_input("Nombre", value=d_name)
                proj_bank = st.selectbox("Banco", bank_ids, index=bank_ids.index(d_bank) if d_bank in bank_ids else 0) if bank_ids else st.text_input("Banco ID", value=d_bank)
                proj_status = st.selectbox("Estado", status_options, index=status_options.index(d_status) if d_status in status_options else 0)
            with col2:
                proj_budget = st.number_input("Presupuesto (USD)", value=d_budget, min_value=0.0, step=10000.0)
                proj_start = st.date_input("Fecha de Inicio", value=d_start)
                proj_end = st.date_input("Fecha de Fin", value=d_end or date.today())
                has_end = st.checkbox("Tiene fecha de fin", value=d_end is not None)

            proj_desc = st.text_area("Descripción", value=d_desc, height=100)

            # Stakeholder selection
            all_personnel_ids = list(personnel_map.keys())
            proj_stakeholders = st.multiselect(
                "Stakeholders",
                options=all_personnel_ids,
                default=[s for s in d_stakeholders if s in all_personnel_ids],
                format_func=lambda x: personnel_map.get(x, x),
            )

            submitted = st.form_submit_button("💾 Guardar Proyecto")
            if submitted:
                if not proj_id or not proj_name:
                    st.error("ID y Nombre son obligatorios.")
                elif not bank_ids and not d_bank:
                    st.error("Debes crear un banco primero.")
                else:
                    entity = ProjectEntity(
                        project_id=proj_id,
                        bank_id=proj_bank if bank_ids else d_bank,
                        name=proj_name,
                        description=proj_desc,
                        status=proj_status,
                        budget_usd=proj_budget,
                        start_date=proj_start,
                        end_date=proj_end if has_end else None,
                        stakeholder_ids=proj_stakeholders,
                    )
                    insert_project(session, entity)
                    session.commit()
                    st.success(f"Proyecto '{proj_name}' guardado correctamente.")
                    st.rerun()

        # ---- Delete ----
        if projects:
            st.subheader("Eliminar Proyecto")
            del_id = st.selectbox("Seleccionar proyecto a eliminar", existing_ids, key="proj_del")
            if st.button("🗑️ Eliminar Proyecto", type="secondary"):
                _delete_row(session, ProjectRow, "project_id", del_id)
                st.success(f"Proyecto '{del_id}' eliminado.")
                st.rerun()
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: PERSONAL (Stakeholders)
# ═══════════════════════════════════════════════════════════════════════════

elif page == "👥 Personal":
    st.header("👥 Gestión de Personal / Stakeholders")
    session = _get_db()

    try:
        personnel = get_all_personnel(session)
        banks = get_all_banks(session)
        bank_map = {b.bank_id: b.name for b in banks}

        # ---- Table view ----
        if personnel:
            st.subheader("Personal registrado")
            pers_data = [
                {
                    "ID": p.personnel_id,
                    "Nombre": p.full_name,
                    "Rol": p.role.value,
                    "Departamento": p.department,
                    "Banco": bank_map.get(p.bank_id, p.bank_id),
                    "Email": p.email,
                    "Experiencia (años)": p.years_experience,
                }
                for p in personnel
            ]
            st.dataframe(pers_data, use_container_width=True, hide_index=True)
        else:
            st.info("No hay personal registrado.")

        # ---- Add / Edit ----
        st.subheader("Agregar / Editar Personal")

        existing_ids = [p.personnel_id for p in personnel]
        edit_mode = st.toggle("Modo edición", key="pers_edit_toggle")

        if edit_mode and personnel:
            selected_id = st.selectbox("Seleccionar personal", existing_ids, key="pers_select")
            sel = next(p for p in personnel if p.personnel_id == selected_id)
            d_id = sel.personnel_id
            d_bank = sel.bank_id
            d_name = sel.full_name
            d_role = sel.role.value
            d_dept = sel.department
            d_email = sel.email
            d_exp = sel.years_experience
            id_disabled = True
        else:
            existing_nums = [int(p.personnel_id.split("-")[1]) for p in personnel if "-" in p.personnel_id]
            next_num = max(existing_nums, default=0) + 1
            d_id = f"PER-{next_num:03d}"
            d_bank = banks[0].bank_id if banks else ""
            d_name = ""
            d_role = "developer"
            d_dept = ""
            d_email = ""
            d_exp = 1
            id_disabled = False

        bank_ids = [b.bank_id for b in banks]
        role_options = [r.value for r in PersonnelRole]

        with st.form("personnel_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                pers_id = st.text_input("ID del Personal", value=d_id, disabled=id_disabled)
                full_name = st.text_input("Nombre Completo", value=d_name)
                role = st.selectbox("Rol", role_options, index=role_options.index(d_role) if d_role in role_options else 0)
                department = st.text_input("Departamento", value=d_dept)
            with col2:
                pers_bank = st.selectbox("Banco", bank_ids, index=bank_ids.index(d_bank) if d_bank in bank_ids else 0) if bank_ids else st.text_input("Banco ID", value=d_bank)
                email = st.text_input("Email Corporativo", value=d_email)
                years_exp = st.number_input("Años de Experiencia", value=d_exp, min_value=0, max_value=50, step=1)

            submitted = st.form_submit_button("💾 Guardar Personal")
            if submitted:
                if not pers_id or not full_name:
                    st.error("ID y Nombre son obligatorios.")
                else:
                    entity = PersonnelEntity(
                        personnel_id=pers_id,
                        bank_id=pers_bank if bank_ids else d_bank,
                        full_name=full_name,
                        role=role,
                        department=department,
                        email=email,
                        years_experience=int(years_exp),
                    )
                    insert_personnel(session, entity)
                    session.commit()
                    st.success(f"Personal '{full_name}' guardado correctamente.")
                    st.rerun()

        # ---- Delete ----
        if personnel:
            st.subheader("Eliminar Personal")
            del_id = st.selectbox("Seleccionar personal a eliminar", existing_ids, key="pers_del")
            if st.button("🗑️ Eliminar Personal", type="secondary"):
                _delete_row(session, PersonnelRow, "personnel_id", del_id)
                st.success(f"Personal '{del_id}' eliminado.")
                st.rerun()
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: REGULACIONES
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📜 Regulaciones":
    st.header("📜 Gestión de Regulaciones")
    session = _get_db()

    try:
        regulations = get_all_regulations(session)
        banks = get_all_banks(session)
        bank_map = {b.bank_id: b.name for b in banks}

        # ---- Table view ----
        if regulations:
            st.subheader("Regulaciones registradas")
            reg_data = [
                {
                    "ID": r.regulation_id,
                    "Código": r.code,
                    "Título": r.title,
                    "Emisor": r.issuing_body,
                    "Vigencia": str(r.effective_date),
                    "Bancos Aplicables": ", ".join(
                        bank_map.get(bid, bid) for bid in r.applicable_bank_ids
                    ),
                }
                for r in regulations
            ]
            st.dataframe(reg_data, use_container_width=True, hide_index=True)
        else:
            st.info("No hay regulaciones registradas.")

        # ---- Add / Edit ----
        st.subheader("Agregar / Editar Regulación")

        existing_ids = [r.regulation_id for r in regulations]
        edit_mode = st.toggle("Modo edición", key="reg_edit_toggle")

        if edit_mode and regulations:
            selected_id = st.selectbox("Seleccionar regulación", existing_ids, key="reg_select")
            sel = next(r for r in regulations if r.regulation_id == selected_id)
            d_id = sel.regulation_id
            d_code = sel.code
            d_title = sel.title
            d_issuer = sel.issuing_body
            d_date = sel.effective_date
            d_summary = sel.summary
            d_bank_ids = sel.applicable_bank_ids
            id_disabled = True
        else:
            existing_nums = [int(r.regulation_id.split("-")[1]) for r in regulations if "-" in r.regulation_id]
            next_num = max(existing_nums, default=0) + 1
            d_id = f"REG-{next_num:03d}"
            d_code = ""
            d_title = ""
            d_issuer = ""
            d_date = date.today()
            d_summary = ""
            d_bank_ids = []
            id_disabled = False

        bank_ids = [b.bank_id for b in banks]

        with st.form("regulation_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                reg_id = st.text_input("ID de Regulación", value=d_id, disabled=id_disabled)
                reg_code = st.text_input("Código (ej. Basel III)", value=d_code)
                reg_title = st.text_input("Título", value=d_title)
            with col2:
                reg_issuer = st.text_input("Entidad Emisora", value=d_issuer)
                reg_date = st.date_input("Fecha de Vigencia", value=d_date)
                reg_banks = st.multiselect(
                    "Bancos Aplicables",
                    options=bank_ids,
                    default=[bid for bid in d_bank_ids if bid in bank_ids],
                    format_func=lambda x: f"{x} — {bank_map.get(x, '')}",
                ) if bank_ids else []

            reg_summary = st.text_area("Resumen", value=d_summary, height=100)

            submitted = st.form_submit_button("💾 Guardar Regulación")
            if submitted:
                if not reg_id or not reg_code or not reg_title:
                    st.error("ID, Código y Título son obligatorios.")
                else:
                    entity = RegulationEntity(
                        regulation_id=reg_id,
                        code=reg_code,
                        title=reg_title,
                        issuing_body=reg_issuer,
                        effective_date=reg_date,
                        summary=reg_summary,
                        applicable_bank_ids=reg_banks if bank_ids else [],
                    )
                    insert_regulation(session, entity)
                    session.commit()
                    st.success(f"Regulación '{reg_title}' guardada correctamente.")
                    st.rerun()

        # ---- Delete ----
        if regulations:
            st.subheader("Eliminar Regulación")
            del_id = st.selectbox("Seleccionar regulación a eliminar", existing_ids, key="reg_del")
            if st.button("🗑️ Eliminar Regulación", type="secondary"):
                _delete_row(session, RegulationRow, "regulation_id", del_id)
                st.success(f"Regulación '{del_id}' eliminada.")
                st.rerun()
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: GENERAR DOCUMENTOS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "🚀 Generar Documentos":
    from datetime import datetime as _gen_dt
    from src.workflow.generator import DocumentGenerator as _DocGen
    from src.formatting.renderer import PDFRenderer as _PDFRenderer

    st.header("🚀 Generar Documentación Completa de Proyecto")
    st.caption(
        "Genera el paquete completo de documentos para un proyecto: RFP, Anexo Técnico, "
        "Actas de Reunión, Preguntas y Respuestas de RFP e Historial del Proyecto."
    )

    session = _get_db()
    try:
        _gen_banks = get_all_banks(session)
        _gen_projects = get_all_projects(session)

        if not _gen_banks:
            st.warning("No hay bancos registrados. Crea uno en la sección Bancos.")
        elif not _gen_projects:
            st.warning("No hay proyectos registrados. Crea uno en la sección Proyectos.")
        else:
            _gen_bank_map = {b.bank_id: b.name for b in _gen_banks}

            col_left, col_right = st.columns([3, 2])

            with col_left:
                st.subheader("⚙️ Configuración")

                _sel_bank_id = st.selectbox(
                    "Banco",
                    [b.bank_id for b in _gen_banks],
                    format_func=lambda x: f"{_gen_bank_map[x]} ({x})",
                    key="gen_bank_sel",
                )

                _bank_projs = [p for p in _gen_projects if p.bank_id == _sel_bank_id]
                if not _bank_projs:
                    st.warning(
                        "Este banco no tiene proyectos asignados. "
                        "Crea uno en la sección Proyectos."
                    )
                else:
                    _sel_proj = st.selectbox(
                        "Proyecto",
                        _bank_projs,
                        format_func=lambda p: f"{p.project_id} — {p.name}",
                        key="gen_proj_sel",
                    )

                    # Optional evolution event link
                    _gen_profile = get_bank_profile(session, _sel_bank_id)
                    if _gen_profile and _gen_profile.evolution_history:
                        st.markdown("**Relacionar con hito de evolución (opcional)**")
                        _use_evo = st.checkbox(
                            "Asociar a un hito registrado en la Fuente de la Verdad",
                            key="gen_use_evo",
                        )
                        if _use_evo:
                            _sel_evo = st.selectbox(
                                "Hito de Evolución",
                                _gen_profile.evolution_history,
                                format_func=lambda e: f"{e.event_date} — {e.title}",
                                key="gen_evo_sel",
                            )
                            st.info(
                                f"📌 **{_sel_evo.title}** ({_sel_evo.event_date})\n\n"
                                f"{_sel_evo.description}"
                            )

                    st.divider()
                    st.markdown("**Tipos de documento a generar**")

                    _gen_row1, _gen_row2 = st.columns(2)
                    _sel_types: list[str] = []
                    for _gidx, (_gdt, (_gicon, _glabel, _gdesc)) in enumerate(
                        _DOC_TYPE_META.items()
                    ):
                        with (_gen_row1 if _gidx % 2 == 0 else _gen_row2):
                            if st.checkbox(
                                f"{_gicon} {_glabel}",
                                value=True,
                                help=_gdesc,
                                key=f"gentype_{_gdt}",
                            ):
                                _sel_types.append(_gdt)

                    st.divider()

                    if not _sel_types:
                        st.warning("Selecciona al menos un tipo de documento.")
                    else:
                        _gen_btn = st.button(
                            f"🚀 Generar {len(_sel_types)} documento"
                            f"{'s' if len(_sel_types) != 1 else ''}",
                            type="primary",
                            use_container_width=True,
                            key="gen_start_btn",
                        )

                        if _gen_btn:
                            _gen_generator = _DocGen()
                            _gen_renderer = _PDFRenderer()
                            _gen_generated: list[tuple] = []

                            _gen_progress = st.progress(
                                0, text="Iniciando generación..."
                            )
                            _gen_results = st.container()

                            for _gi, _gdt in enumerate(_sel_types):
                                _gicon, _glabel, _ = _DOC_TYPE_META[_gdt]
                                _gen_progress.progress(
                                    int((_gi / len(_sel_types)) * 100),
                                    text=(
                                        f"Generando {_gicon} {_glabel} "
                                        f"({_gi + 1}/{len(_sel_types)})..."
                                    ),
                                )
                                try:
                                    _res = _gen_generator.generate(
                                        project_id=_sel_proj.project_id,
                                        doc_type=_gdt,
                                    )
                                    _final_md = _res.get("final_markdown", "")
                                    if not _final_md:
                                        with _gen_results:
                                            st.warning(
                                                f"⚠️ **{_glabel}**: no se obtuvo contenido"
                                            )
                                        continue

                                    _proj_data = _res.get("project", {})
                                    _skel = _res.get("skeleton", {})
                                    _xmp = {
                                        "title": _skel.get("metadata", {}).get(
                                            "title",
                                            f"{_gdt}_{_sel_proj.project_id}",
                                        ),
                                        "document_type": _gdt,
                                        "project_id": _sel_proj.project_id,
                                        "bank_id": _proj_data.get(
                                            "bank_id", _sel_bank_id
                                        ),
                                        "stakeholder_ids": _proj_data.get(
                                            "stakeholder_ids", []
                                        ),
                                    }
                                    _ts = _gen_dt.now().strftime("%Y%m%d_%H%M%S")
                                    _fname = f"{_gdt}_{_sel_proj.project_id}_{_ts}"
                                    _pdf = _gen_renderer.render(
                                        markdown=_final_md,
                                        filename=_fname,
                                        metadata=_xmp,
                                    )
                                    _gen_generated.append((
                                        _gdt,
                                        _glabel,
                                        _pdf,
                                        _res.get("token_usage", {}),
                                    ))
                                    with _gen_results:
                                        st.success(
                                            f"✅ **{_gicon} {_glabel}** — `{_pdf.name}`"
                                        )
                                except Exception as _gexc:
                                    with _gen_results:
                                        st.error(f"❌ **{_glabel}**: {_gexc}")

                            _gen_progress.progress(100, text="¡Generación completa!")

                            if _gen_generated:
                                _total_tok = sum(
                                    g[3].get("total_tokens", 0)
                                    for g in _gen_generated
                                )
                                st.success(
                                    f"🎉 **{len(_gen_generated)} documento(s) generado(s)** — "
                                    f"{_total_tok:,} tokens en total. "
                                    "Revisa la sección **📄 Documentos Generados**."
                                )

            with col_right:
                st.subheader("ℹ️ Guía de tipos de documento")
                for _gdt, (_gicon, _glabel, _gdesc) in _DOC_TYPE_META.items():
                    with st.expander(f"{_gicon} {_glabel}"):
                        st.caption(_gdesc)
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: DOCUMENTOS GENERADOS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📄 Documentos Generados":
    st.header("📄 Documentos Generados")

    output_dir = settings.OUTPUT_DIR

    # Scan output directory for PDF + XMP pairs
    pdf_files = sorted(output_dir.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not pdf_files:
        st.info("No se han generado documentos aún. Usa el CLI o la pestaña de generación.")
    else:
        # Parse metadata from XMP sidecars and file names
        documents = []
        for pdf in pdf_files:
            xmp_path = pdf.with_suffix(".xmp")
            meta = _parse_xmp(xmp_path) if xmp_path.exists() else {}

            # Parse info from filename: {doc_type}_{project_id}_{seq}.pdf
            parts = pdf.stem.split("_")
            doc_type = parts[0] if len(parts) >= 1 else "unknown"
            project_id = parts[1] if len(parts) >= 2 else "—"

            stat = pdf.stat()
            documents.append({
                "filename": pdf.name,
                "path": pdf,
                "doc_type": meta.get("documentClass", doc_type),
                "project_id": meta.get("projectId", project_id),
                "bank_id": meta.get("bankId", "—"),
                "title": meta.get("title", pdf.stem),
                "stakeholders": meta.get("stakeholder_ids", []),
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime),
            })

        # ---- Filters ----
        st.subheader("🔍 Filtros de Búsqueda")

        session = _get_db()
        try:
            banks = get_all_banks(session)
            bank_map = {b.bank_id: b.name for b in banks}
        finally:
            session.close()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            doc_types = sorted(set(d["doc_type"] for d in documents))
            type_labels = {
                dt: lbl
                for dt, (_, lbl, _desc) in _DOC_TYPE_META.items()
            }
            type_labels["regulation_summary"] = "Resumen Regulatorio"
            filter_type = st.multiselect(
                "Tipo de Documento",
                options=doc_types,
                format_func=lambda x: type_labels.get(x, x),
            )

        with col2:
            bank_ids_in_docs = sorted(set(d["bank_id"] for d in documents if d["bank_id"] != "—"))
            filter_bank = st.multiselect(
                "Empresa / Banco",
                options=bank_ids_in_docs,
                format_func=lambda x: f"{bank_map.get(x, x)} ({x})",
            )

        with col3:
            filter_project = st.text_input("ID de Proyecto (ej. PRJ-001)", key="filter_proj")

        with col4:
            min_date = min(d["created"] for d in documents).date()
            max_date = max(d["created"] for d in documents).date()
            date_range = st.date_input(
                "Rango de Fechas",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="filter_dates",
            )

        # Text search in title
        filter_text = st.text_input("🔎 Buscar en título del documento", key="filter_text")

        # Apply filters
        filtered = documents
        if filter_type:
            filtered = [d for d in filtered if d["doc_type"] in filter_type]
        if filter_bank:
            filtered = [d for d in filtered if d["bank_id"] in filter_bank]
        if filter_project:
            filtered = [d for d in filtered if filter_project.upper() in d["project_id"].upper()]
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_dt, end_dt = date_range
            filtered = [
                d for d in filtered
                if start_dt <= d["created"].date() <= end_dt
            ]
        if filter_text:
            search_lower = filter_text.lower()
            filtered = [d for d in filtered if search_lower in d["title"].lower()]

        # ---- Results ----
        st.divider()
        st.subheader(f"📋 Resultados ({len(filtered)} documento{'s' if len(filtered) != 1 else ''})")

        if not filtered:
            st.warning("No se encontraron documentos con los filtros aplicados.")
        else:
            for doc in filtered:
                type_icon = _DOC_TYPE_META.get(doc["doc_type"], ("📄", "", ""))[0]

                with st.expander(
                    f"{type_icon} {doc['title'][:80]}  —  {doc['project_id']}  |  "
                    f"{doc['created'].strftime('%Y-%m-%d %H:%M')}  |  {doc['size_kb']} KB"
                ):
                    col_info, col_actions = st.columns([3, 1])

                    with col_info:
                        st.markdown(f"**Archivo:** `{doc['filename']}`")
                        st.markdown(f"**Tipo:** {type_labels.get(doc['doc_type'], doc['doc_type'])}")
                        st.markdown(f"**Proyecto:** {doc['project_id']}")
                        st.markdown(f"**Banco:** {bank_map.get(doc['bank_id'], doc['bank_id'])}")
                        st.markdown(f"**Generado:** {doc['created'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**Tamaño:** {doc['size_kb']} KB")
                        if doc["stakeholders"]:
                            st.markdown(f"**Stakeholders:** {', '.join(doc['stakeholders'])}")

                    with col_actions:
                        # Download button
                        with open(doc["path"], "rb") as f:
                            st.download_button(
                                "⬇️ Descargar PDF",
                                data=f.read(),
                                file_name=doc["filename"],
                                mime="application/pdf",
                                key=f"dl_{doc['filename']}",
                            )

                        # Show XMP if exists
                        xmp_path = doc["path"].with_suffix(".xmp")
                        if xmp_path.exists():
                            with open(xmp_path, "r", encoding="utf-8") as xf:
                                st.download_button(
                                    "📎 Descargar XMP",
                                    data=xf.read(),
                                    file_name=xmp_path.name,
                                    mime="application/xml",
                                    key=f"xmp_{doc['filename']}",
                                )
