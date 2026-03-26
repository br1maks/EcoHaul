
import sys
import uvicorn

def main():

    kwargs = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False,
    }

    if "--reload" in sys.argv:
        kwargs["reload"] = True
        print("🔄 Автоперезагрузка включена")

    if "--sandbox" in sys.argv:
        kwargs["env_file"] = ".env.sandbox"
        print("🧪 Запуск в SANDBOX режиме")

    if "--port" in sys.argv:
        try:
            port_index = sys.argv.index("--port") + 1
            kwargs["port"] = int(sys.argv[port_index])
            print(f"📡 Порт: {kwargs['port']}")
        except (IndexError, ValueError):
            print("❌ Неверный формат порта")
            sys.exit(1)

    print("=" * 60)
    print("🚀 Запуск EcoHaul API сервера...")
    print("=" * 60)
    print(f"📍 URL: http://{kwargs['host']}:{kwargs['port']}")
    print(f"📚 Swagger: http://{kwargs['host']}:{kwargs['port']}/api/docs")
    print("=" * 60)
    print()

    uvicorn.run(**kwargs)

if __name__ == "__main__":
    main()
