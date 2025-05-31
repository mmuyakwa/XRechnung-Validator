import os
import requests
import gradio as gr
import anthropic
import markdown
import PyPDF2
import xml.etree.ElementTree as ET
from io import BytesIO
import zipfile
import fitz  # PyMuPDF für bessere PDF-Verarbeitung

"""
Zu importierende Pakete:

anthropic
gradio
requests
markdown
PyPDF2
PyMuPDF
"""

# Umgebungsvariablen
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
validator_host = os.environ.get("VALIDATOR_HOST")
validator_port = os.environ.get("VALIDATOR_PORT")
url = f"http://{validator_host}:{validator_port}"

# Anthropic Client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def check_api_availability(url):
    """Überprüft, ob die API erreichbar ist"""
    try:
        response = requests.head(url, timeout=5)
        print(f"Rückgabewert: {response} => {response.status_code}")
        return response.status_code < 400
    except requests.RequestException:
        return False

def send_xml_data(url, xml_data):
    """Sendet eine XML-Datei an die angegebene URL"""
    try:
        headers = {"Content-Type": "application/xml"}
        response = requests.post(url, headers=headers, data=xml_data)
        if response.status_code < 400:
            print(f"Success: The request was successfully sent. Status code: {response.status_code}")
            print("Response:", response.text)
            return response.text
        else:
            print(f"Error message: The request was not successful. Status code: {response.status_code}")
            print("Antwort:", response.text)
            return response.text
    except Exception as e:
        print(f"A error occurred while sending the request: {e}")
        return f"Connection to the validator-api was not possible. Error: {e}"

def extract_xml_from_zugferd_pdf(pdf_file):
    """Extrahiert XML aus ZUGFeRD-PDF-Datei"""
    try:
        # Versuche zuerst mit PyMuPDF (fitz)
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        # Suche nach eingebetteten Dateien (Attachments)
        for i in range(pdf_document.embfile_count()):
            embfile_info = pdf_document.embfile_info(i)
            filename = embfile_info.get("filename", "")
            
            # ZUGFeRD XML-Dateien haben typischerweise diese Namen
            if filename.lower() in ["zugferd-invoice.xml", "factur-x.xml", "xrechnung.xml"] or filename.lower().endswith(".xml"):
                embfile_content = pdf_document.embfile_get(i)
                xml_content = embfile_content.decode('utf-8')
                pdf_document.close()
                return xml_content, f"✅ XML erfolgreich aus PDF extrahiert: {filename}"
        
        pdf_document.close()
        
        # Fallback: Versuche mit PyPDF2
        pdf_file.seek(0)  # Reset file pointer
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        
        # Prüfe auf eingebettete Dateien in den Metadaten
        if "/EmbeddedFiles" in pdf_reader.trailer.get("/Root", {}):
            return None, "❌ PDF enthält eingebettete Dateien, aber XML-Extraktion fehlgeschlagen"
            
        return None, "❌ Keine XML-Datei in der PDF gefunden. Stellen Sie sicher, dass es sich um eine ZUGFeRD-PDF handelt."
        
    except Exception as e:
        return None, f"❌ Fehler beim Extrahieren der XML aus PDF: {str(e)}"

def validate_xml_content(xml_content):
    """Validiert, ob der Inhalt gültiges XML ist"""
    try:
        ET.fromstring(xml_content)
        return True, "✅ XML-Format ist gültig"
    except ET.ParseError as e:
        return False, f"❌ XML-Format ungültig: {str(e)}"
    except Exception as e:
        return False, f"❌ Fehler bei XML-Validierung: {str(e)}"

def process_uploaded_file(file):
    """Verarbeitet hochgeladene Datei (XML oder PDF)"""
    if file is None:
        return None, "❌ Keine Datei hochgeladen"
    
    filename = file.name.lower()
    
    try:
        if filename.endswith('.xml'):
            # XML-Datei direkt verarbeiten
            xml_content = file.read().decode('utf-8')
            is_valid, message = validate_xml_content(xml_content)
            if is_valid:
                return xml_content, f"✅ XML-Datei erfolgreich geladen: {file.name}"
            else:
                return None, message
                
        elif filename.endswith('.pdf'):
            # PDF-Datei verarbeiten und XML extrahieren
            file.seek(0)  # Reset file pointer
            xml_content, message = extract_xml_from_zugferd_pdf(file)
            if xml_content:
                is_valid, validation_message = validate_xml_content(xml_content)
                if is_valid:
                    return xml_content, message
                else:
                    return None, f"{message}\n{validation_message}"
            else:
                return None, message
        else:
            return None, "❌ Nicht unterstütztes Dateiformat. Bitte laden Sie eine XML- oder PDF-Datei hoch."
            
    except Exception as e:
        return None, f"❌ Fehler beim Verarbeiten der Datei: {str(e)}"

def create_analysis_response_stream(xml_content, error_message):
    """Analysiert XML-Rechnung mit Anthropic API und gibt Stream zurück"""
    prompt = f"""# 📊 Advanced Invoice Processing System

You are an advanced invoice processing system designed to analyze XML invoices, identify errors, and provide corrections. Your task is to examine the following XML content and error message, then provide a comprehensive analysis and correction.

## 📄 Invoice XML Content
... Here is the XML content of the invoice:

<invoice_xml>
{xml_content}
</invoice_xml>

## ❗ Error Message

Here is the error message associated with this invoice:

<error_message>
{error_message}
</error_message>

## 🔍 Analysis and Correction Process

Please follow these steps to analyze and correct the invoice. Use Markdown formatting and emojis where appropriate to make your output more readable and engaging.

1. **Review and Analyze**: 
   Carefully review the XML content and the error message. In your analysis, include the following:
   - List all XML nodes and their values, numbering them as you go.
   - Identify and list all errors found in the XML.
   - For misplaced XML nodes, explain their correct placement.
   - Recalculate all totals in the invoice, showing your work for each step. (Always use ❌ to highlight found discrepancies and ✅ to highlight correct calculations. This eases identifying problems.)
   - Verify if the gross sum is consistent with the net sums and payable taxes.

2. **Summarize Findings**:
   Provide a clear summary of your findings, including:
   - A list of all errors found
   - Corrections for misplaced XML nodes
   - Any discrepancies found in calculations

3. **Detailed Calculations**:
   Show a detailed breakdown of:
   - Position-level sums with surcharges/discounts
   - Tax amounts for each tax rate
   - Taxable net sums
   - Payable tax sums
   - Verification of gross sum consistency

4. **Corrected XML**:
   Provide the complete XML in its corrected form. (Umklammere es mit ``````, um es ordentlich im Markdown zu formatieren.)

5. **XML Comparison**:
   Compare the original and corrected XML side-by-side, highlighting the changes made.

## 📝 Output Structure

Please structure your response as follows:

## 🔬 Invoice Analysis

[Your detailed invoice review here. Follow these steps:... 1. List all XML nodes and their values, numbering them.
2. Identify and list all errors, numbering them.
3. For misplaced nodes, explain their correct placement.
4. Recalculate totals, showing work for each step.
5. Verify gross sum consistency with net sums and payable taxes.
It's okay for this section to be quite long, as it involves detailed analysis.]

## 📊 Error Summary
[Summary of errors and corrections here]

## 🧮 Detailed Calculations
[Detailed calculation breakdown here]

## ✅ Corrected XML

[Corrected XML here]

## 🔄 XML Comparison
[Side-by-side comparison of original and corrected XML]

Ensure that your analysis is thorough and all calculations are accurate. This will help maintain the consistency and correctness of the invoice data."""

    try:
        with client.messages.stream(
            model="claude-3-7-sonnet-latest",
            max_tokens=12800,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            accumulated_text = ""
            for text in stream.text_stream:
                accumulated_text += text
                html_output = markdown.markdown(
                    accumulated_text, extensions=["fenced_code", "tables", "codehilite"]
                )
                yield html_output

    except anthropic.APIStatusError as e:
        yield f"Anthropic API-Fehler: {e}"
    except anthropic.APIConnectionError as e:
        yield f"Anthropic API-Verbindungsfehler: {e}"
    except anthropic.RateLimitError as e:
        yield f"Anthropic API-Rate-Limit erreicht: {e}"
    except Exception as e:
        yield f"Ein unerwarteter Fehler ist aufgetreten: {e}"

def process_xml_streaming(xml_input):
    """Verarbeitet XML-Text Input"""
    if not xml_input.strip():
        yield "❌ Bitte geben Sie XML-Inhalt ein oder laden Sie eine Datei hoch."
        return
        
    error_input = send_xml_data(url, xml_input)
    if "Connection to the validator-api was not possible" in error_input:
        yield "❌ Der XML-Validator ist nicht erreichbar. Bitte stellen Sie sicher, dass der Server läuft."
        return
    
    yield from create_analysis_response_stream(xml_input, error_input)

def process_file_upload_streaming(file):
    """Verarbeitet hochgeladene Datei"""
    xml_content, status_message = process_uploaded_file(file)
    
    if xml_content is None:
        yield status_message
        return
    
    # Zeige Status-Nachricht an
    yield f"{status_message}\n\n---\n\n🔄 **Starte Validierung...**"
    
    error_input = send_xml_data(url, xml_content)
    if "Connection to the validator-api was not possible" in error_input:
        yield f"{status_message}\n\n---\n\n❌ **Der XML-Validator ist nicht erreichbar. Bitte stellen Sie sicher, dass der Server läuft.**"
        return
    
    # Füge den Status zur finalen Analyse hinzu
    final_status = f"{status_message}\n\n---\n\n"
    
    accumulated_text = ""
    for html_chunk in create_analysis_response_stream(xml_content, error_input):
        accumulated_text = html_chunk
        yield final_status + accumulated_text

# Gradio Interface
with gr.Blocks(theme=gr.themes.Monochrome(primary_hue="slate", secondary_hue="gray")) as iface:
    gr.Markdown("""
    # 🧾 XML-Rechnungsanalyse mit Anthropic AI
    
    **Analysieren und korrigieren Sie XML-Rechnungen (XRechnung/ZUGFeRD) mit KI-Unterstützung**
    
    Wählen Sie eine der folgenden Optionen:
    """)
    
    with gr.Tabs():
        # Tab 1: Datei-Upload
        with gr.TabItem("📁 Datei hochladen"):
            gr.Markdown("""
            ### Laden Sie Ihre Datei hoch:
            - **XML-Dateien**: Direkte Analyse der XML-Rechnung
            - **PDF-Dateien**: Automatische Extraktion der XML aus ZUGFeRD-PDFs
            """)
            
            file_input = gr.File(
                label="XML- oder ZUGFeRD-PDF-Datei hochladen",
                file_types=[".xml", ".pdf"],
                type="binary"
            )
            
            analyze_file_button = gr.Button("🔍 Datei analysieren und korrigieren", variant="primary")
            
            output_file_html = gr.HTML(label="📊 Analyseergebnis")
            
            analyze_file_button.click(
                fn=process_file_upload_streaming,
                inputs=file_input,
                outputs=output_file_html
            )
        
        # Tab 2: Text-Eingabe
        with gr.TabItem("✏️ XML-Text eingeben"):
            gr.Markdown("""
            ### XML-Inhalt direkt eingeben:
            Fügen Sie den kompletten XML-Inhalt Ihrer Rechnung in das Textfeld ein.
            """)
            
            xml_input = gr.Textbox(
                label="📄 XML-Rechnung (XRechnung/ZUGFeRD)",
                lines=15,
                placeholder="Fügen Sie hier den XML-Inhalt Ihrer Rechnung ein..."
            )
            
            analyze_text_button = gr.Button("🔍 XML analysieren und korrigieren", variant="primary")
            
            output_text_html = gr.HTML(label="📊 Analyseergebnis")
            
            analyze_text_button.click(
                fn=process_xml_streaming,
                inputs=xml_input,
                outputs=output_text_html
            )
    
    # Footer mit Informationen
    gr.Markdown("""
    ---
    **💡 Hinweise:**
    - ZUGFeRD-PDFs enthalten die XML-Rechnung als eingebetteten Anhang
    - Die KI analysiert Fehler und schlägt Korrekturen vor
    - Alle Berechnungen werden detailliert überprüft und korrigiert
    """)

# App starten
PORT = 7860
iface.launch(server_name="0.0.0.0", server_port=PORT)