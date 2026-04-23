import google.generativeai as genai
# ใส่ API Key ของคุณ
genai.configure(api_key="ใส่_API_KEY_ของคุณที่นี่")

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)