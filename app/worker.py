import time


def main() -> None:
    print("Worker placeholder running. Background queue integration can be enabled with RQ/Celery.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
