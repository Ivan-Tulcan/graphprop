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

            # Load existing profile or create empty
            profile = get_bank_profile(session, selected_bank)
            if profile is None:
                profile = BankProfile(bank_id=selected_bank)
                st.info("Este banco aún no tiene perfil. Completa los campos y guarda.")

            # ---- TABS for structured sections ----
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

            # ---- TAB: Estrategia ----
            with tab_strategy:
                st.subheader("🎯 Estrategia y Visión")
                with st.form("profile_strategy", clear_on_submit=False):
                    p_mission = st.text_area("Misión", value=profile.mission, height=80)
                    p_vision = st.text_area("Visión", value=profile.vision, height=80)
                    p_objectives = st.text_area(
                        "Objetivos Estratégicos (uno por línea)",
                        value="\n".join(profile.strategic_objectives),
                        height=120,
                    )
                    p_advantages = st.text_area(
                        "Ventajas Competitivas (una por línea)",
                        value="\n".join(profile.competitive_advantages),
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

            # ---- TAB: Procesos ----
            with tab_processes:
                st.subheader("⚙️ Procesos de Negocio")
                with st.form("profile_processes", clear_on_submit=False):
                    p_core = st.text_area(
                        "Procesos Core (uno por línea)",
                        value="\n".join(profile.core_processes),
                        height=120,
                        help="Ej: Captaciones, Colocaciones, Pagos, Comercio Exterior, Tesorería",
                    )
                    p_support = st.text_area(
                        "Procesos de Soporte (uno por línea)",
                        value="\n".join(profile.support_processes),
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

            # ---- TAB: Tecnología ----
            with tab_tech:
                st.subheader("💻 Stack Tecnológico")
                with st.form("profile_tech", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        p_core_sys = st.text_input("Core Bancario", value=profile.core_banking_system, help="Ej: Temenos T24, Finacle, Cobis")
                        p_langs = st.text_area("Lenguajes de Programación (uno por línea)", value="\n".join(profile.programming_languages), height=80)
                        p_dbs = st.text_area("Bases de Datos (una por línea)", value="\n".join(profile.databases), height=80)
                        p_cloud = st.text_area("Proveedores Cloud (uno por línea)", value="\n".join(profile.cloud_providers), height=60)
                    with col2:
                        p_devops = st.text_area("Herramientas DevOps (una por línea)", value="\n".join(profile.devops_tools), height=80)
                        p_integration = st.text_area("Middleware/Integración (uno por línea)", value="\n".join(profile.integration_middleware), height=80)
                        p_security = st.text_area("Stack de Seguridad (uno por línea)", value="\n".join(profile.security_stack), height=80)
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

            # ---- TAB: Arquitectura ----
            with tab_arch:
                st.subheader("🏗️ Arquitectura Empresarial y Tecnológica")
                with st.form("profile_arch", clear_on_submit=False):
                    p_arch_style = st.selectbox(
                        "Estilo de Arquitectura",
                        ["Monolítica", "SOA", "Microservicios", "Híbrida", "Event-Driven", "Otro"],
                        index=["Monolítica", "SOA", "Microservicios", "Híbrida", "Event-Driven", "Otro"].index(profile.architecture_style) if profile.architecture_style in ["Monolítica", "SOA", "Microservicios", "Híbrida", "Event-Driven", "Otro"] else 0,
                    )
                    p_arch_layers = st.text_area(
                        "Capas de Arquitectura (una por línea)",
                        value="\n".join(profile.architecture_layers),
                        height=100,
                        help="Ej: Capa de Presentación, Capa de Servicios, Capa de Negocio, Capa de Datos",
                    )
                    p_key_systems = st.text_area(
                        "Sistemas Clave (uno por línea)",
                        value="\n".join(profile.key_systems),
                        height=100,
                        help="Ej: Core Bancario, CRM, ERP, Data Warehouse, Motor de Riesgos",
                    )
                    p_ext_int = st.text_area(
                        "Integraciones Externas (una por línea)",
                        value="\n".join(profile.external_integrations),
                        height=80,
                        help="Ej: SWIFT, Visa/Mastercard, Buró de Crédito, Regulador",
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        p_data_plat = st.text_area("Plataforma de Datos", value=profile.data_platform, height=60)
                    with col2:
                        p_analytics = st.text_area("Herramientas de Analítica (una por línea)", value="\n".join(profile.analytics_tools), height=60)
                    p_ai = st.text_area(
                        "Capacidades AI/ML (una por línea)",
                        value="\n".join(profile.ai_ml_capabilities),
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

            # ---- TAB: Canales ----
            with tab_channels:
                st.subheader("📡 Canales")
                with st.form("profile_channels", clear_on_submit=False):
                    p_digital = st.text_area(
                        "Canales Digitales (uno por línea)",
                        value="\n".join(profile.digital_channels),
                        height=80,
                        help="Ej: App Móvil, Banca Web, Chatbot, WhatsApp Banking",
                    )
                    p_physical = st.text_area(
                        "Canales Físicos (uno por línea)",
                        value="\n".join(profile.physical_channels),
                        height=80,
                        help="Ej: Agencias, Cajeros ATM, Kioscos, Corresponsales",
                    )
                    p_partner = st.text_area(
                        "Canales de Terceros/Partners (uno por línea)",
                        value="\n".join(profile.partner_channels),
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

            # ---- TAB: Organización ----
            with tab_org:
                st.subheader("🏢 Estructura Organizacional")
                with st.form("profile_org", clear_on_submit=False):
                    p_org_notes = st.text_area(
                        "Notas sobre Estructura Organizacional",
                        value=profile.org_structure_notes,
                        height=100,
                    )
                    p_depts = st.text_area(
                        "Departamentos Clave (uno por línea)",
                        value="\n".join(profile.key_departments),
                        height=100,
                    )
                    if st.form_submit_button("💾 Guardar Organización"):
                        profile.org_structure_notes = p_org_notes
                        profile.key_departments = [x.strip() for x in p_depts.strip().splitlines() if x.strip()]
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Organización guardada.")
                        st.rerun()

            # ---- TAB: Evolución ----
            with tab_history:
                st.subheader("📈 Historial de Evolución")
                st.caption(
                    "Registra hitos importantes: apertura de canales, migraciones de core, "
                    "modernizaciones tecnológicas, adquisiciones, nuevos servicios, etc."
                )

                # Show existing events
                if profile.evolution_history:
                    for idx, evt in enumerate(profile.evolution_history):
                        cat_icons = {
                            "canal": "📡", "modernización": "🚀", "migración": "🔄",
                            "servicio": "➕", "adquisición": "🤝", "otro": "📌",
                        }
                        icon = cat_icons.get(evt.category, "📌")
                        with st.expander(f"{icon} {evt.event_date} — {evt.title}"):
                            st.markdown(f"**Categoría:** {evt.category}")
                            st.markdown(f"**Descripción:** {evt.description}")
                            if st.button(f"❌ Eliminar evento", key=f"del_evt_{idx}"):
                                profile.evolution_history.pop(idx)
                                upsert_bank_profile(session, profile)
                                session.commit()
                                st.rerun()
                else:
                    st.info("No hay eventos registrados aún.")

                # Add new event
                st.markdown("---")
                st.markdown("**Agregar Nuevo Evento**")
                with st.form("add_event", clear_on_submit=True):
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
                            # Sort chronologically
                            profile.evolution_history.sort(key=lambda e: e.event_date)
                            upsert_bank_profile(session, profile)
                            session.commit()
                            st.success(f"Evento '{evt_title}' agregado.")
                            st.rerun()

            # ---- TAB: Contexto Adicional ----
            with tab_extra:
                st.subheader("📝 Contexto Adicional")
                with st.form("profile_extra", clear_on_submit=False):
                    p_extra = st.text_area(
                        "Notas adicionales (texto libre)",
                        value=profile.additional_context,
                        height=200,
                        help="Cualquier información adicional que no encaje en las otras secciones.",
                    )
                    if st.form_submit_button("💾 Guardar Contexto"):
                        profile.additional_context = p_extra
                        upsert_bank_profile(session, profile)
                        session.commit()
                        st.success("Contexto adicional guardado.")
                        st.rerun()

            # ---- TAB: JSON Completo ----
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
                    key="profile_json_editor",
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
                "rfp": "RFP (Solicitud de Propuestas)",
                "project_history": "Historial de Proyecto",
                "meeting_minutes": "Acta de Reunión",
                "technical_annex": "Anexo Técnico",
                "regulation_summary": "Resumen Regulatorio",
            }
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
                type_icon = {
                    "rfp": "📝",
                    "project_history": "📊",
                    "meeting_minutes": "📋",
                }.get(doc["doc_type"], "📄")

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
