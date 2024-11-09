try:
    while True:
        inp = input()
        print(f"{len(inp)} events were created")
except KeyboardInterrupt:
    print()
    print("exiting...")
