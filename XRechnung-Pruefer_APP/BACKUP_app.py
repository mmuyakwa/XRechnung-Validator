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
    prompt = f"""You are an advanced invoice processing system designed to analyze XML invoices, identify errors, and provide corrections. Your task is to examine the provided XML content and error message, then provide a comprehensive analysis and correction.

Here is the XML content of the invoice:

<xml_content>
{xml_content}
</xml_content>

Here is the error message associated with this invoice:

<error_message>
{error_message}
</error_message>

Please follow these steps to analyze and correct the invoice:

1. Determine Invoice Type:
   Begin by identifying whether the invoice is a Credit Note, Direct Debit, or normal Invoice. Use the following guidelines:
   - Direct Debit: Look for the "DIRECT DEBIT" (BG-19) group or Payment means type code (BT-81) with code 59.
   - Credit Note: Check for invoice type codes 381 (Credit note) or 261 (Self billed credit note), or negative total amounts with codes 380, 384, or 389.
   - Normal Invoice: If neither of the above conditions are met, assume it's a normal invoice.

2. Review and Analyze:
   Carefully review the XML content and the error message. In your analysis, include the following:
   - List all XML nodes and their values, numbering them as you go.
   - Identify and list all errors found in the XML.
   - For misplaced XML nodes, explain their correct placement.
   - Recalculate all totals in the invoice, showing your work for each step. Use ❌ to highlight discrepancies and ✅ for correct calculations.
   - Verify if the gross sum is consistent with the net sums and payable taxes.

3. Summarize Findings:
   Provide a clear summary of your findings, including:
   - A list of all errors found
   - Corrections for misplaced XML nodes
   - Any discrepancies found in calculations

4. Detailed Calculations:
   Show a detailed breakdown of:
   - Position-level sums with surcharges/discounts
   - Tax amounts for each tax rate
   - Taxable net sums
   - Payable tax sums
   - Verification of gross sum consistency

5. Corrected XML:
   Provide the complete XML in its corrected form.

6. XML Comparison:
   Compare the original and corrected XML side-by-side, highlighting the changes made.

Please structure your response as follows:

```markdown
# Invoice Analysis Report

## Invoice Type
[State whether the invoice is a Credit Note, Direct Debit, or normal Invoice, and explain why]

## 🔬 Detailed Analysis
[Your detailed invoice review here, following the steps outlined above]

## 📊 Error Summary
[Summary of errors and corrections]

## 🧮 Detailed Calculations
[Detailed calculation breakdown]

## ✅ Corrected XML
```xml
[Corrected XML here]
```

## 🔄 XML Comparison
[Side-by-side comparison of original and corrected XML]
```

Before providing your final response, wrap your thought process in <invoice_analysis> tags. This will ensure a thorough interpretation of the data. In this section:

1. List out each XML node and its value, numbering them as you go.
2. For error analysis, consider each possible error type separately.
3. Show your work for each calculation step, using ❌ to highlight discrepancies and ✅ for correct calculations.

It's OK for this section to be quite long.

Remember to use Markdown formatting and emojis where appropriate to make your output more readable and engaging. Ensure that your analysis is thorough and all calculations are accurate to maintain the consistency and correctness of the invoice data."""

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
