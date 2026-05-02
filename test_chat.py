from agents import react_agent

if __name__ == "__main__":
    print("Testing React Agent...")
    try:
        resp = react_agent.run_query("Hello! Test message.", [])
        print("Response:", resp)
    except Exception as e:
        import traceback
        traceback.print_exc()
