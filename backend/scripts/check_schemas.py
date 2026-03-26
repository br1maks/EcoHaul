import sys
import re
from pathlib import Path

def extract_model_fields(model_file):
    content = model_file.read_text()
    fields = []
    for line in content.split('\n'):
        if ': Mapped[' in line:
            match = re.search(r'(\w+):\s*Mapped\[', line)
            if match:
                fields.append(match.group(1))
    return sorted(fields)

def extract_schema_fields(schema_file, class_name):
    content = schema_file.read_text()
    in_class = False
    fields = []

    for line in content.split('\n'):
        if f'class {class_name}' in line:
            in_class = True
            continue
        if in_class:
            if line.startswith('class ') and 'class_name' not in line:
                break
            if line.strip().startswith('def ') or line.strip().startswith('@'):
                break
            match = re.match(r'\s+(\w+):\s*', line)
            if match and not match.group(1).startswith('_'):
                fields.append(match.group(1))

    return sorted(fields)

def main():
    models_to_check = [
        ('wallet_transaction', 'WalletTransactionBase'),
        ('review', 'ReviewBase'),
        ('notification', 'NotificationBase'),
        ('courier_shift', 'CourierShiftBase'),
        ('payment', 'PaymentBase'),
    ]

    print("=" * 80)
    print("ПРОВЕРКА СООТВЕТСТВИЯ СХЕМ МОДЕЛЯМ")
    print("=" * 80)

    all_ok = True

    for model_name, schema_class in models_to_check:
        print(f"\n{model_name.upper()}:")
        print("-" * 80)

        model_file = Path(f'app/models/{model_name}.py')
        schema_file = Path(f'app/schemas/{model_name}.py')

        if not model_file.exists():
            print(f"  ❌ Model file not found: {model_file}")
            all_ok = False
            continue

        if not schema_file.exists():
            print(f"  ❌ Schema file not found: {schema_file}")
            all_ok = False
            continue

        model_fields = extract_model_fields(model_file)
        schema_fields = extract_schema_fields(schema_file, schema_class)

        print(f"  Model fields ({len(model_fields)}): {', '.join(model_fields[:5])}...")
        print(f"  Schema fields ({len(schema_fields)}): {', '.join(schema_fields[:5])}...")

        missing_in_schema = set(model_fields) - set(schema_fields)
        extra_in_schema = set(schema_fields) - set(model_fields)

        if missing_in_schema:
            print(f"  ⚠️  Missing in schema: {', '.join(sorted(missing_in_schema))}")

        if extra_in_schema:
            print(f"  ⚠️  Extra in schema: {', '.join(sorted(extra_in_schema))}")

        if not missing_in_schema and not extra_in_schema:
            print(f"  ✅ All fields match!")
        else:
            all_ok = False

    print("\n" + "=" * 80)
    if all_ok:
        print("✅ ВСЕ СХЕМЫ СООТВЕТСТВУЮТ МОДЕЛЯМ")
    else:
        print("⚠️  ОБНАРУЖЕНЫ РАСХОЖДЕНИЯ (проверьте выше)")
    print("=" * 80)

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
