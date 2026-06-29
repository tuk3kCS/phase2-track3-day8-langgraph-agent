from pathlib import Path

# Paths
traces_path = Path("outputs/execution_traces_hidden.json")
html_path = Path("report.html")

# Read files
traces_json = traces_path.read_text(encoding="utf-8")
html_content = html_path.read_text(encoding="utf-8")

# Injection points
start_tag = '<script id="real-traces-data" type="application/json">'
end_tag = '</script>'

if start_tag in html_content and end_tag in html_content:
    before, rest = html_content.split(start_tag, 1)
    _, after = rest.split(end_tag, 1)
    new_html = f"{before}{start_tag}\n{traces_json}\n{end_tag}{after}"
    html_path.write_text(new_html, encoding="utf-8")
    print("SUCCESS: Injected hidden scenarios traces into report.html")
else:
    print("ERROR: Injection tags not found in report.html")
