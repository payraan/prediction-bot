import os
import traceback

def main():
    print("=== BOOT CHECK ===")
    print("PYTHONPATH:", os.getcwd())
    print("PORT:", os.getenv("PORT"))
    print("DATABASE_URL set:", bool(os.getenv("DATABASE_URL")))
    print("TON_HOUSE_WALLET_ADDRESS set:", bool(os.getenv("TON_HOUSE_WALLET_ADDRESS")))
    print("TON_NETWORK:", os.getenv("TON_NETWORK"))

    try:
        print("\n--- Trying to import src.api.main ---")
        from src.api.main import app
        print("✅ Imported src.api.main:app OK")
        routes = [getattr(r, "path", None) for r in app.router.routes]
        print("Routes:", [p for p in routes if p])
    except Exception:
        print("❌ Import failed:")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
