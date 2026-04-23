import google.generativeai as genai
from django.shortcuts import render
from django.http import JsonResponse
import os
import json
import re
import requests
from gtts import gTTS
from django.conf import settings
from .models import ContentHistory
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from PIL import Image # เพิ่มบรรทัดนี้ด้านบนสุด
from dotenv import load_dotenv

load_dotenv()

# ดึง Key มาใช้งานอย่างปลอดภัย
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

def home(request):
    best_selling_products = [
        {'id': 1, 'name': 'ลิปสติกเนื้อแมตต์ กันน้ำ', 'sales': '1.2k', 'price': '159'},
        {'id': 2, 'name': 'ครีมกันแดด SPF50 PA+++', 'sales': '2.5k', 'price': '290'},
        {'id': 3, 'name': 'หูฟังบลูทูธไร้สาย Pro', 'sales': '800', 'price': '590'},
    ]
    return render(request, 'index.html', {'products': best_selling_products})

@csrf_exempt # ปลดล็อกความปลอดภัยเพราะเราใช้ POST
def generate_content(request):
    try:
        # รับข้อมูลจากแบบฟอร์ม (เปลี่ยนจาก GET เป็น POST)
        product_name = request.POST.get('product_name', '')
        gen_type = request.POST.get('type', 'all')
        image_files = request.FILES.getlist('images')
        
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        if gen_type == 'caption':
            prompt_instruction = '"caption": "เขียนแคปชั่นขายของให้น่าสนใจ พร้อม hashtag"'
        elif gen_type == 'script':
            prompt_instruction = '"script": "เขียนสคริปต์พากย์เสียงสั้นๆ 15 วินาที กระชับและดึงดูด"'
        else:
            prompt_instruction = '"caption": "เขียนแคปชั่นพร้อม hashtag",\n            "script": "เขียนสคริปต์พากย์เสียง 15 วินาที"'

        prompt_text = f"""
        ฉันมีข้อมูลต้นทางคือ: "{product_name}"
        (หากมีรูปภาพแนบมาด้วย ให้วิเคราะห์รายละเอียดจากรูปภาพทั้งหมดเพื่อเขียนเนื้อหา)
        
        กรุณาสร้างเนื้อหาและตอบกลับเป็น JSON format ตามโครงสร้างนี้เท่านั้น:
        {{
            "short_name": "สรุปชื่อสินค้าสั้นๆ (ไม่เกิน 40 ตัวอักษร)",
            {prompt_instruction}
        }}
        """
        
        prompt_content = [prompt_text]
        
        # วนลูปเปิดรูปภาพทุกใบที่อัปโหลดมาให้ AI ดู
        if image_files:
            for img_file in image_files:
                img = Image.open(img_file)
                prompt_content.append(img)
        
        response = model.generate_content(prompt_content)
        text = response.text
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        json_str = match.group() if match else text
        data = json.loads(json_str)
        
        final_product_name = data.get('short_name', product_name)
        if len(final_product_name) > 100:
            final_product_name = final_product_name[:100] + "..."
        
        ContentHistory.objects.create(
            product_name=final_product_name,
            caption=data.get('caption', ''),
            script=data.get('script', '')
        )

        return JsonResponse({
            'caption': data.get('caption', ''),
            'script': data.get('script', '')
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def text_to_speech(request):
    text = request.GET.get('text', '')
    if text:
        tts_path = os.path.join(settings.BASE_DIR, 'core/static/audio/')
        if not os.path.exists(tts_path):
            os.makedirs(tts_path)
            
        tts = gTTS(text=text, lang='th')
        filename = "narration.mp3"
        tts.save(os.path.join(tts_path, filename))
        
        return JsonResponse({'audio_url': '/static/audio/' + filename})
    return JsonResponse({'error': 'No text provided'}, status=400)

def get_history(request):
    try:
        history = ContentHistory.objects.all().order_by('-created_at')[:10]
        data = []
        for item in history:
            data.append({
                'id': item.id,  # <-- สิ่งที่เพิ่มเข้ามาเพื่อให้รู้ว่าต้องลบอันไหน
                'product_name': item.product_name,
                'caption': item.caption,
                'script': item.script,
                'date': item.created_at.strftime("%d/%m/%Y %H:%M")
            })
        return JsonResponse({'history': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ฟังก์ชันใหม่สำหรับลบเฉพาะชิ้นที่เลือก
def delete_history_item(request, item_id):
    try:
        item = ContentHistory.objects.get(id=item_id)
        item.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def clear_history(request):
    try:
        # สั่งลบข้อมูลทั้งหมดในตาราง ContentHistory
        ContentHistory.objects.all().delete()
        return JsonResponse({'status': 'success', 'message': 'ล้างประวัติเรียบร้อยแล้ว'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt  # <-- เพิ่มคำนี้เพื่อบอก Django ว่า "ทางนี้ปลอดภัย ปล่อยผ่านได้เลย"
def generate_video(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            uploaded_file = request.FILES['image']
            
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            image_url = fs.url(filename)
            
            import time
            time.sleep(3) 
            
            return JsonResponse({
                'status': 'success',
                'message': 'AI สร้างวิดีโอเสร็จสมบูรณ์',
                'original_image': image_url,
                'video_url': '/static/videos/dummy_video.mp4' 
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'No image uploaded'}, status=400)