import os
import requests
import gradio as gr
import anthropic
import markdown

# Laden der Umgebungsvariablen aus der .env-Datei
# from dotenv import load_dotenv
# load_dotenv(override=True)
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

validator_host = os.environ.get("VALIDATOR_HOST")
validator_port = os.environ.get("VALIDATOR_PORT")

# url = "http://localhost:8080"
url = f"http://{validator_host}:{validator_port}"


# Initialisierung des Anthropic-Clients
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
            print(
                f"Success: The request was successfully sent. Status code: {response.status_code}"
            )
            print("Response:", response.text)
            return response.text
        else:
            print(
                f"Error message: The request was not successful. Status code: {response.status_code}"
            )
            print("Antwort:", response.text)
            return response.text
    except Exception as e:
        print(f"A error occurred while sending the request: {e}")
        return f"Connection to the validator-api was not possible. Error: {e}"


def create_analysis_response_stream(xml_content, error_message):
    """
    Analysiert eine XML-Rechnung und eine Fehlermeldung mithilfe der Anthropic API,
    um Fehler verständlich zu erklären und eine korrigierte XML-Version zu erstellen.
    Gibt die Antwort als Stream zurück.
    """
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
        # Stream für die Antwort erstellen
        with client.messages.stream(
            # model="claude-3-7-sonnet-20250219",
            model="claude-3-7-sonnet-latest",
            max_tokens=12800,
            # max_tokens=8192,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            # Aktualisierter Text für die Ausgabe
            accumulated_text = ""

            # Für jedes Teilstück der Antwort im Textstream
            for text in stream.text_stream:
                accumulated_text += text
                # Markdown-Text in HTML konvertieren
                html_output = markdown.markdown(
                    accumulated_text, extensions=["fenced_code", "tables", "codehilite"]
                )
                # Yield für Gradio-Streaming
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
    error_input = send_xml_data(url, xml_input)
    if error_input == "Connection to the validator-api was not possible.":
        yield "The XML validator is not reachable. Please ensure that the server is running."
        return
    # Die Antwort als Stream weitergeben
    yield from create_analysis_response_stream(xml_input, error_input)


# Gradio Interface erstellen
with gr.Blocks(
    theme=gr.themes.Monochrome(primary_hue="slate", secondary_hue="gray")
) as iface:
    gr.Markdown("# Analyse XML-Rechnung with Anthropic")
    with gr.Row():
        xml_input = gr.Textbox(label="XML-Rechnung (XRechnung/ZUGFeRD)", lines=10)
    analyze_button = gr.Button("Analyze and correct")

    # HTML-Ausgabe für gestreamte Anzeige (ohne streaming=True!)
    output_html = gr.HTML(label="Result of analysis and corrections of the XML")

    # Streaming-Version der Prozessierungsfunktion
    analyze_button.click(
        fn=process_xml_streaming, inputs=xml_input, outputs=output_html
    )

# Starten der Gradio App mit einem bestimmten Port
PORT = 7860  # Setze hier deinen gewünschten Port
iface.launch(server_name="0.0.0.0", server_port=PORT)
