"""
PDF Rendering Pipeline.

Converts generated Markdown documents into high-fidelity corporate PDFs:
  1. Markdown → HTML5 (via pandoc or fallback Python markdown)
  2. HTML5 → PDF (via WeasyPrint with custom CSS)
  3. Inject XMP metadata (document class, project ID, stakeholder IDs)
"""

import subprocess
import re
import shutil
import xml.etree.ElementTree as ET
import base64
import zlib
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings
from src.exceptions import RenderingError
from src.logger import setup_logger

logger = setup_logger("formatting.renderer")

# Path to the corporate CSS stylesheet
_CSS_PATH = settings.PROJECT_ROOT / "config" / "document.css"


class PDFRenderer:
    """
    Renders Markdown content into professionally formatted PDFs.

    Uses pandoc for Markdown→HTML conversion and WeasyPrint for
    HTML→PDF rendering with a custom CSS stylesheet.
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        css_path: Path | None = None,
    ) -> None:
        self.output_dir = output_dir or settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.css_path = css_path or _CSS_PATH
        self._pandoc_available = shutil.which("pandoc") is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        markdown: str,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Render Markdown to a PDF file.

        Args:
            markdown: The Markdown content to render.
            filename: Output filename (without extension).
            metadata: Optional XMP metadata dict (project_id, stakeholder_ids, etc.).

        Returns:
            Path to the generated PDF file.
        """
        logger.info("Rendering PDF: %s", filename)

        # Step 0: Render architecture diagrams using Kroki (C4-PlantUML / Mermaid)
        markdown = self._process_kroki_diagrams(markdown)

        # Step 1: Convert Markdown → HTML5
        html = self._markdown_to_html(markdown)

        # Step 2: Wrap HTML with CSS and metadata
        full_html = self._wrap_html(html, metadata)

        # Step 3: Render HTML → PDF via WeasyPrint
        pdf_path = self.output_dir / f"{filename}.pdf"
        self._html_to_pdf(full_html, pdf_path)

        # Step 4: Inject XMP metadata into the PDF
        if metadata:
            self._inject_xmp_metadata(pdf_path, metadata)

        logger.info("PDF rendered successfully: %s", pdf_path)
        return pdf_path

    # ------------------------------------------------------------------
    # Step 1: Markdown → HTML & Diagram Processing
    # ------------------------------------------------------------------

    def _process_kroki_diagrams(self, markdown: str) -> str:
        """
        Intercept diagram code blocks (C4-PlantUML, PlantUML, Mermaid) and 
        replace them with rendered images from the Kroki API using Data URIs.
        Falls back to the raw code block if API fails.
        """
        pattern = re.compile(r'```(c4plantuml|plantuml|mermaid)\s*\n(.*?)```', flags=re.DOTALL | re.IGNORECASE)

        def replacer(match: re.Match) -> str:
            diag_type = match.group(1).strip().lower()
            code = match.group(2).strip()

            try:
                # Use POST to Kroki to avoid GET URL length limits for large diagrams
                import json
                
                url = "https://kroki.io/"
                payload = {
                    "diagram_source": code,
                    "diagram_type": diag_type,
                    "output_format": "png"
                }
                
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'SDF-C4-Renderer/1.0'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=20) as resp:
                    img_data = resp.read()
                    
                # Base64 encode the received PNG bytes
                b64_img = base64.b64encode(img_data).decode('ascii')
                data_uri = f"data:image/png;base64,{b64_img}"
                
                # Return standard HTML <img> tag
                # Note: 'height: auto' can cause layout errors in xhtml2pdf (NoneType comparisons),
                # so we use a fixed width or just let it scale naturally.
                return (
                    f'\n<div class="diagram-render" style="text-align: center; margin: 20px 0;">\n'
                    f'  <img src="{data_uri}" alt="{diag_type} Diagram" style="width: 100%;" />\n'
                    f'</div>\n'
                )
            except Exception as exc:
                logger.warning("Kroki API render failed for %s: %s. Using fallback.", diag_type, exc)
                return match.group(0)

        return pattern.sub(replacer, markdown)

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert Markdown to HTML5, using pandoc if available."""
        if self._pandoc_available:
            return self._pandoc_convert(markdown)
        return self._fallback_convert(markdown)

    def _pandoc_convert(self, markdown: str) -> str:
        """Use pandoc subprocess for high-quality Markdown → HTML5 conversion."""
        try:
            result = subprocess.run(
                [
                    "pandoc",
                    "--from=markdown",
                    "--to=html5",
                    "--no-highlight",
                ],
                input=markdown.encode("utf-8"),  # explicit UTF-8 bytes to pandoc
                capture_output=True,
                timeout=30,
                check=True,
            )
            logger.debug("Pandoc conversion successful")
            return result.stdout.decode("utf-8")  # decode pandoc output as UTF-8
        except (subprocess.CalledProcessError, FileNotFoundError, UnicodeError) as exc:
            logger.warning("Pandoc failed, using fallback converter: %s", exc)
            return self._fallback_convert(markdown)

    def _fallback_convert(self, markdown_text: str) -> str:
        """
        Convert Markdown to HTML using the Python 'markdown' library.

        Supports tables, fenced code blocks, and all standard Markdown
        syntax — handles accented characters and Unicode correctly.
        """
        import markdown as md

        return md.markdown(
            markdown_text,
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
        )

    # ------------------------------------------------------------------
    # Step 2: Wrap HTML with CSS
    # ------------------------------------------------------------------

    def _wrap_html(
        self,
        body_html: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Wrap the body HTML in a full HTML5 document with CSS."""
        css_content = ""
        if self.css_path.exists():
            css_content = self.css_path.read_text(encoding="utf-8")

        # Build metadata block if present
        meta_block = ""
        if metadata:
            items = "".join(
                f"<dt>{k}:</dt><dd>{v}</dd> "
                for k, v in metadata.items()
                if not isinstance(v, (list, dict))
            )
            meta_block = f'<div class="metadata"><dl>{items}</dl></div>'

        title = metadata.get("title", "Document") if metadata else "Document"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{css_content}</style>
</head>
<body>
{meta_block}
{body_html}
</body>
</html>"""

    # ------------------------------------------------------------------
    # Step 3: HTML → PDF via WeasyPrint (with xhtml2pdf fallback)
    # ------------------------------------------------------------------

    def _html_to_pdf(self, html: str, output_path: Path) -> None:
        """
        Render the HTML string to a PDF file.

        Tries WeasyPrint first (best quality, requires GTK system libs).
        Falls back to xhtml2pdf (pure Python, works on all platforms).
        """
        # Try WeasyPrint first
        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(str(output_path))
            logger.debug("WeasyPrint rendered PDF: %s", output_path)
            return
        except (ImportError, OSError) as exc:
            logger.info("WeasyPrint unavailable (%s), using xhtml2pdf fallback.", exc)

        # Fallback: xhtml2pdf (pure Python, no system libs required)
        try:
            from xhtml2pdf import pisa

            # xhtml2pdf does not support @page margin boxes (@top-center, etc.)
            # Strip them with regex to avoid its CSS parser raising TypeError.
            clean_html = re.sub(
                r'@(?:top|bottom|left|right)-[a-z-]+\s*\{[^}]*\}',
                '',
                html,
            )

            # Pass HTML as a string so xhtml2pdf uses the <meta charset="utf-8">
            # declared in the document — avoids Latin-1 mojibake on Windows.
            with open(output_path, "wb") as pdf_file:
                result = pisa.CreatePDF(
                    clean_html,
                    dest=pdf_file,
                )

            if result.err:
                raise RenderingError(
                    f"xhtml2pdf reported {result.err} error(s) during rendering."
                )
            logger.debug("xhtml2pdf rendered PDF: %s", output_path)
        except ImportError:
            raise RenderingError(
                "No PDF renderer available. Install weasyprint (with GTK) "
                "or xhtml2pdf: pip install xhtml2pdf"
            )
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"PDF rendering failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Step 4: XMP Metadata Injection
    # ------------------------------------------------------------------

    def _inject_xmp_metadata(
        self,
        pdf_path: Path,
        metadata: dict[str, Any],
    ) -> None:
        """
        Inject XMP metadata into the PDF for GraphRAG ingestion.

        Creates an XMP sidecar (.xmp) file next to the PDF containing
        structured metadata (project_id, document_class, stakeholder_ids).
        This approach avoids rewriting the PDF binary.
        """
        xmp_path = pdf_path.with_suffix(".xmp")

        # Build XMP XML
        rdf_ns = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        dc_ns = "http://purl.org/dc/elements/1.1/"
        sdf_ns = "http://syntheticdocfactory.io/xmp/1.0/"

        root = ET.Element("x:xmpmeta", xmlns_x="adobe:ns:meta/")
        rdf = ET.SubElement(root, f"{{{rdf_ns}}}RDF")
        desc = ET.SubElement(
            rdf,
            f"{{{rdf_ns}}}Description",
            attrib={
                f"{{{rdf_ns}}}about": "",
                f"{{{dc_ns}}}title": metadata.get("title", ""),
                f"{{{sdf_ns}}}projectId": metadata.get("project_id", ""),
                f"{{{sdf_ns}}}documentClass": metadata.get("document_type", ""),
                f"{{{sdf_ns}}}bankId": metadata.get("bank_id", ""),
            },
        )

        # Stakeholder IDs as a sequence
        stakeholders = metadata.get("stakeholder_ids", [])
        if stakeholders:
            bag = ET.SubElement(
                ET.SubElement(desc, f"{{{sdf_ns}}}stakeholderIds"),
                f"{{{rdf_ns}}}Bag",
            )
            for sid in stakeholders:
                li = ET.SubElement(bag, f"{{{rdf_ns}}}li")
                li.text = str(sid)

        # Write XMP sidecar
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(xmp_path), encoding="unicode", xml_declaration=True)
        logger.info("XMP metadata written: %s", xmp_path)
