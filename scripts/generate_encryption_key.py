import base64
import secrets
from pathlib import Path

VARIABLE_NAME = "DATA_ENCRYPTION_KEY"


def generate_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []

    for index, line in enumerate(lines):
        if not line.startswith(f"{VARIABLE_NAME}="):
            continue
        if line.partition("=")[2].strip():
            print(f"{VARIABLE_NAME} is already configured in .env")
            return
        lines[index] = f"{VARIABLE_NAME}={generate_key()}"
        break
    else:
        lines.append(f"{VARIABLE_NAME}={generate_key()}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"A new {VARIABLE_NAME} was saved to .env")


if __name__ == "__main__":
    main()
