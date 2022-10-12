from src.main import server, scheduler

if __name__ == "__main__":
    scheduler.start()
    server.run()