import base64
import io
import re
import cv2
import numpy as np
from datetime import datetime
import pytesseract
from pytesseract import Output
import platform

# If running on Windows, point to the default installation path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def parse_trx_from_image(image_bytes):
    """
    Parses a screenshot of a transaction history using lightweight Tesseract OCR.
    Finds the date labels to segment the transactions.
    Each physical segment above a date is processed into one transaction block.
    """
    # Read image from bytes for OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Convert to grayscale for better OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Try to execute tesseract
    try:
        results = pytesseract.image_to_data(gray, output_type=Output.DICT)
    except Exception as e:
        print(f"Failed to run Tesseract: {e}")
        return []

    raw_words = []
    screen_width = img.shape[1]
    
    n_boxes = len(results['text'])
    for i in range(n_boxes):
        text = results['text'][i].strip()
        # Filter low confidence artifacts and empty text
        if int(results['conf'][i]) > 10 and len(text) > 0:
            x, y, w, h = results['left'][i], results['top'][i], results['width'][i], results['height'][i]
            
            mid_y = y + h / 2
            mid_x = x + w / 2
            
            raw_words.append({
                'text': text,
                'mid_y': mid_y,
                'mid_x': mid_x,
                'y_min': y,
                'y_max': y + h,
                'x_min': x,
                'x_max': x + w
            })
            
    # Group words horizontally into lines
    horizontal_tolerance = 15
    raw_lines = []
    
    for word in raw_words:
        added = False
        for line in raw_lines:
            if abs(line['mid_y'] - word['mid_y']) < horizontal_tolerance:
                line['words'].append(word)
                added = True
                break
        if not added:
            raw_lines.append({
                'mid_y': word['mid_y'],
                'words': [word]
            })

    # Group phrases based on distance
    elements = []
    for line in raw_lines:
        line['words'].sort(key=lambda w: w['mid_x']) # left to right
        
        chunks = []
        current_chunk = [line['words'][0]]
        x_tolerance = 120 # distance between far-left and far-right columns
        
        for word in line['words'][1:]:
            prev_word = current_chunk[-1]
            dist = word['x_min'] - prev_word['x_max']
            if dist < x_tolerance:
                current_chunk.append(word)
            else:
                chunks.append(current_chunk)
                current_chunk = [word]
        chunks.append(current_chunk)
        
        for chunk in chunks:
            text = " ".join([w['text'] for w in chunk])
            y_min = min([w['y_min'] for w in chunk])
            y_max = max([w['y_max'] for w in chunk])
            x_min = min([w['x_min'] for w in chunk])
            x_max = max([w['x_max'] for w in chunk])
            mid_y = (y_min + y_max) / 2
            mid_x = (x_min + x_max) / 2
            
            elements.append({
                'text': text,
                'mid_y': mid_y,
                'mid_x': mid_x,
                'y_min': y_min,
                'y_max': y_max,
                'x_min': x_min,
                'x_max': x_max,
                'is_right': mid_x > screen_width / 2
            })
            
    # Sort elements top to bottom
    elements.sort(key=lambda x: x['mid_y'])
    
    # Date pattern DD Bulan YYYY (e.g. 03 Maret 2026)
    date_pattern = re.compile(r'^\d{1,2}\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}$', re.IGNORECASE)
    
    # Let's find index of date boundaries
    date_indices = []
    for i, el in enumerate(elements):
        if date_pattern.match(el['text']):
            date_indices.append(i)
            
    transactions = []
    
    for i in range(len(date_indices)):
        date_idx = date_indices[i]
        date_text = elements[date_idx]['text']
        
        # Elements for this transaction boundary are the ones ABOVE this date
        start_idx = date_indices[i-1] + 1 if i > 0 else 0
        end_idx = date_idx
        
        block = elements[start_idx:end_idx]
        
        if not block:
            continue
            
        rows = []
        current_row = [block[0]]
        y_tolerance = 25
        
        for el in block[1:]:
            if abs(el['mid_y'] - current_row[0]['mid_y']) < y_tolerance:
                current_row.append(el)
            else:
                rows.append(current_row)
                current_row = [el]
        if current_row:
            rows.append(current_row)
            
        amount = 0
        tx_type = ""
        amount_found = False
        note = ""
        tags = ""
        
        idx = 0
        while idx < len(rows):
            row = rows[idx]
            for item in row:
                if 'Rp' in item['text']:
                    text = item['text'].replace('.', '').replace(',', '')
                    match = re.search(r'([\+\-]?)\s*Rp\s*(\d+)', text, re.IGNORECASE)
                    if match:
                        sign = match.group(1)
                        amount_val = int(match.group(2))
                        tx_type = "income" if sign == '+' else "expense"
                        amount = amount_val
                        amount_found = True
                        
                        left_items = [x['text'] for x in row if not x['is_right'] and x != item]
                        desc1 = " ".join(left_items)
                        
                        desc2 = ""
                        if idx + 1 < len(rows):
                            next_row = rows[idx+1]
                            left_items_next = [x['text'] for x in next_row if not x['is_right']]
                            desc2 = " ".join(left_items_next)
                            tags = left_items_next[0] if left_items_next else ""
                        
                        note = f"{desc1} {desc2}".strip()
                        break
            if amount_found:
                break
            idx += 1
            
        if amount_found:
            transactions.append({
                'date_str': date_text,
                'amount': amount,
                'type': tx_type,
                'note': note,
                'tags': [tags] if tags else []
            })
            
    transactions.reverse()
    
    date_to_current_hour = {}
    
    month_map = {
        'januari': 1, 'jan': 1, 'februari': 2, 'feb': 2, 'maret': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'mei': 5, 'may': 5, 'juni': 6, 'jun': 6,
        'juli': 7, 'jul': 7, 'agustus': 8, 'aug': 8, 'september': 9, 'sep': 9,
        'oktober': 10, 'oct': 10, 'november': 11, 'nov': 11, 'desember': 12, 'dec': 12
    }
    
    def parse_indonesian_date(date_string):
        parts = date_string.lower().split()
        if len(parts) >= 3:
            day = int(parts[0])
            month = month_map.get(parts[1], 1)
            year = int(parts[2])
            return year, month, day
        return datetime.now().year, datetime.now().month, datetime.now().day

    formatted_txs = []
    
    for tx in transactions:
        date_str = tx['date_str']
        if date_str not in date_to_current_hour:
            date_to_current_hour[date_str] = 7 
        else:
            date_to_current_hour[date_str] += 1 
            
        hour = date_to_current_hour[date_str]
        
        y, m, d = parse_indonesian_date(date_str)
        try:
            dt_obj = datetime(y, m, d, hour, 0, 0)
        except ValueError:
            dt_obj = datetime(y, m, d, 23, 59, 59)
            
        tx['timestamp'] = int(dt_obj.timestamp())
        tx['category'] = "General Income" if tx['type'] == 'income' else "General Expense"
        
        formatted_txs.append(tx)
        
    formatted_txs.reverse()
    return formatted_txs
