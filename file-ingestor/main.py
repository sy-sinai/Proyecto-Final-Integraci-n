import time
import os
from csv_processor import parse_csv_file, move_file, get_pending_files, PROCESSED_DIR, ERROR_DIR
from database import SessionLocal
from models import InventoryItem

def process_file(file_path):
    """Procesa un archivo CSV y carga datos a BD."""
    filename = os.path.basename(file_path)
    print(f"\n📄 Procesando: {filename}")
    
    # Parsear CSV
    items, errors = parse_csv_file(file_path)
    
    if errors:
        for error in errors:
            print(f"  ⚠️ {error}")
    
    if not items:
        print(f"  ❌ No se pudieron procesar items válidos")
        move_file(file_path, ERROR_DIR)
        return False
    
    # Guardar en BD
    db = SessionLocal()
    try:
        saved = 0
        updated = 0
        
        for item_data in items:
            existing = db.query(InventoryItem).filter_by(sku=item_data['sku']).first()
            
            if existing:
                existing.name = item_data['name']
                existing.quantity = item_data['quantity']
                existing.price = item_data['price']
                updated += 1
            else:
                new_item = InventoryItem(**item_data)
                db.add(new_item)
                saved += 1
        
        db.commit()
        db.close()
        
        print(f"  ✅ {saved} nuevos items, {updated} actualizados")
        move_file(file_path, PROCESSED_DIR)
        return True
    
    except Exception as e:
        db.rollback()
        db.close()
        print(f"  ❌ Error guardando en BD: {e}")
        move_file(file_path, ERROR_DIR)
        return False

def start_file_ingestor():
    """Monitor de archivos CSV en carpeta inbox."""
    print("🚀 File Ingestor iniciado...")
    print(f"📁 Monitoreando: /app/inbox")
    
    while True:
        files = get_pending_files()
        
        if files:
            for file_path in files:
                process_file(file_path)
        
        time.sleep(10)  # Revisar cada 10 segundos

if __name__ == "__main__":
    start_file_ingestor()
