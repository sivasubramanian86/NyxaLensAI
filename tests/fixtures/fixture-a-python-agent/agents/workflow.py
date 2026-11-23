def call_tool(tool, payload):
    while True:
        try:
            return tool(payload)
        except Exception:
            continue
