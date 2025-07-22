from src.agents.LangBotAgent import LangBotAgent

def main():
    agent = LangBotAgent()
    print("Welcome to LangBot! Type your database question and press Enter (Ctrl+C to exit):")
    try:
        while True:
            user_message = input("You: ")
            agent.ask_database(user_message)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")

if __name__ == "__main__":
    main()