import csv
import os
import shutil
from pathlib import Path

# Carpetas
INBOX_DIR = "/app/inbox"
PROCESSED_DIR = "/app/processed"
ERROR_DIR = "/app/error"

# Crear carpetas si no existen
os.makedirs(INBOX_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)

def parse_csv_file(file_path):
    """
    Parsea un archivo CSV.
    Espera columnas: sku,name,quantity,price
    """
    items = []
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return None, ["CSV vacío"]
            
            required_fields = {'sku', 'name', 'quantity', 'price'}
            if not required_fields.issubset(set(reader.fieldnames or [])):
                return None, [f"Columnas faltantes. Requiere: {required_fields}"]
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    sku = row.get('sku', '').strip()
                    name = row.get('name', '').strip()
                    quantity = int(row.get('quantity', 0))
                    price = float(row.get('price', 0))
                    
                    if not sku or not name:
                        errors.append(f"Fila {row_num}: SKU o nombre vacío")
                        continue
                    
                    items.append({
                        'sku': sku,
                        'name': name,
                        'quantity': quantity,
                        'price': price
                    })
                except (ValueError, TypeError) as e:
                    errors.append(f"Fila {row_num}: Error de tipo - {e}")
        
        return items if items else None, errors
    
    except Exception as e:
        return None, [f"Error leyendo archivo: {e}"]

def move_file(file_path, destination_dir):
    """Mueve archivo a carpeta destino."""
    try:
        filename = os.path.basename(file_path)
        dest_path = os.path.join(destination_dir, filename)
        shutil.move(file_path, dest_path)
        return True
    except Exception as e:
        print(f"❌ Error moviendo archivo: {e}")
        return False

def get_pending_files():
    """Obtiene archivos CSV pendientes en inbox."""
    if not os.path.exists(INBOX_DIR):
        return []
    
    files = [f for f in os.listdir(INBOX_DIR) if f.endswith('.csv')]
    return [os.path.join(INBOX_DIR, f) for f in files]
