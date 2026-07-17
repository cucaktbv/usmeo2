import streamlit as st
import pandas as pd
import json
import os
import re
import time
import requests
from PIL import Image
import io
import concurrent.futures
from google import genai
from google.genai import types

# --- CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(layout="wide", page_title="Amazon US Script Gen (Eagle Edition)")

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Cổng Đăng Nhập Hệ Thống - Thị Trường Mỹ 🇺🇸")
        pwd = st.text_input("Nhập mật khẩu truy cập:", type="password")
        if st.button("Đăng nhập"):
            if pwd == st.secrets["APP_PASSWORD"]: 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Mật khẩu không chính xác!")
        st.stop()
    return True

check_password()

# --- CẤU HÌNH API ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL_ID = "gemini-3-flash-preview"
PRO_MODEL_ID = "gemini-pro-latest"

# --- BIẾN NỘI BỘ & PROMPTS (Dành riêng cho thị trường Mỹ) ---
PERSONA_DICT = {
    "Friendly & Expert (Chuyên gia Thân thiện - KHUYÊN DÙNG)": "Giọng điệu thân thiện, giống một người bạn am hiểu đang tư vấn chân thành. Biến các thông số phức tạp thành ngôn ngữ đơn giản, dễ hiểu. Thường dùng các cụm từ như 'Honestly', 'Here's the deal', 'Real talk'. Tạo độ tin tưởng (trust) cực kỳ cao.",
    "The Deal Hunter (Thánh săn sale)": "Cực kỳ thực tế, tính toán chi li. Trọng tâm là 'Bang for your buck' (Đáng đồng tiền bát gạo). Ghét bị 'rip-off' (lừa đảo/giá ảo). Giọng điệu giống một người bạn đang khuyên cách tiết kiệm tiền hiệu quả nhất.",
    "The Brutally Honest Skeptic (Chuyên gia Bắt bẻ)": "Cực kỳ khó tính, chuyên soi các lỗi nhỏ (tiếng ồn, build quality, bloatware). Luôn tìm kiếm các 'dealbreaker' (điểm trừ chí mạng). Độ trust cực cao vì khi nhân vật này khen 'worth it', khán giả sẽ mua ngay.",
    "The Tech/Aesthetic Snob (Chuyên gia Cao cấp)": "Giọng điệu điềm tĩnh, chuyên nghiệp. Rất quan tâm đến 'sleek design' (thiết kế tinh tế) và hệ sinh thái. Sẽ chê bai không thương tiếc những sản phẩm có vẻ ngoài rẻ tiền (cheap plastic feel).",
    "The Hype Reviewer (Chiến thần Năng lượng)": "Năng lượng cực cao, nhịp độ nhanh. Thường xuyên dùng các từ ngữ mạnh như 'game-changer', 'insane', 'mind-blowing'. Chỉ nên dùng khi sản phẩm thực sự đột phá để tránh cảm giác bán hàng ép buộc (over-promising)."
}

MEME_VAULT = [
    # Khen ngợi / Chốt sale (US Slang)
    "Absolute game-changer, literally. (Thay đổi cuộc chơi luôn, thề.)",
    "Best bang for your buck, hands down. (Đáng đồng tiền bát gạo nhất, không phải bàn.)",
    "An absolute steal at this price point. (Giá này thì đúng là món hời.)",
    "Looks super clean and premium. (Nhìn cực kỳ xịn và tinh tế.)",
    "It costs a pretty penny, but it's an investment. (Hơi đau ví tí nhưng nó là khoản đầu tư xứng đáng.)",
    "A total no-brainer. (Không cần phải nghĩ ngợi nhiều, chốt luôn.)",
    "This thing is an absolute beast. (Con hàng này đúng là quái vật.)",
    "Shut up and take my money! (Đỉnh quá, mua ngay và luôn!)",
    
    # Chê bai / Tạo Trust (US Slang)
    "Total knock-off, do not waste your hard-earned money. (Hàng rác rưởi, đừng phí tiền.)",
    "Feels like cheap plastic in person. (Cầm trên tay cảm giác nhựa rẻ tiền cực kỳ.)",
    "Great on paper, but a huge letdown in reality. (Thông số thì ngon nhưng dùng thực tế thì thất vọng.)",
    "That right there is a massive dealbreaker. (Đó là một điểm trừ chí mạng.)",
    "Honestly, I expected way better for the price. (Nói thật, tầm giá này tôi kỳ vọng nhiều hơn.)",
    "It's loud, clunky, and just annoying. (Nó ồn, cồng kềnh và phát bực.)"
]

P1_TEMPLATE = """AMAZON USA SEO & KEYWORD ANALYST
Bối cảnh: Tôi sẽ gửi tệp dữ liệu từ khóa (.CSV). Bạn hãy lọc bộ từ khóa "Hái ra tiền" (Money Keywords) tối ưu nhất cho kịch bản Video Review Affiliate Amazon Mỹ (Amazon.com).
Thông tin dự án:
- Sản phẩm: {seed_keywords}
- Ngôn ngữ: TIẾNG ANH (US English) BẮT BUỘC.
- Hiện tại là năm 2026.

YÊU CẦU LỌC TỪ KHÓA:
1. Gộp, lọc trùng, chuyển Volume về số nguyên. CHỈ GIỮ LẠI TỪ KHÓA TIẾNG ANH. Loại bỏ các ngôn ngữ lạ, từ khóa vô nghĩa, hoặc từ khóa quá dài (trên 7 từ).
2. Lọc Ý định Người dùng (Affiliate Intent - QUAN TRỌNG NHẤT):
Hãy phân tích ngữ nghĩa của từ khóa theo tiếng Anh để lọc bỏ các nhóm sau:
- LOẠI BỎ Ý định Nấu ăn/Sử dụng (Recipe/Usage Intent): Ví dụ: "how to use", "recipe for", "tutorial", "instructions".
- LOẠI BỎ Ý định Sửa chữa/Kỹ thuật (Repair/Technical Intent): Ví dụ: "not working", "how to fix", "replacement parts", "doesn't work".
- LOẠI BỎ Ý định Giải trí/Thông tin chung: Ví dụ: "history of", "who invented".
- ƯU TIÊN TỐI ĐA Ý định Mua hàng (Commercial Intent): Chứa các từ như "best", "review", "vs", "worth it", "budget", "under 100", "buying guide", "for".
3. Bộ lọc Ý định "Chốt Sale & Bắt Trend" kiểu Mỹ: Giữ lại từ khóa vấn đề: "battery life", "noise level", "durability".
4. Bộ lọc Thương hiệu: Giữ lại từ khóa kết hợp [Brand] + [Product]. CHỈ LOẠI BỎ: Từ khóa tìm đồ cũ (used, craigslist) hoặc sàn đối thủ (walmart, target, ebay).

Dữ liệu đầu vào:
{csv_data}

YÊU CẦU ĐẦU RA (TRẢ VỀ JSON CHÍNH XÁC, GIỮ ĐÚNG FORMAT NÀY):
{
    "detected_brands": ["brand1", "brand2"],
    "keywords": [ {"keyword": "english keyword here", "volume": 10000} ]
}"""

P2_TEMPLATE = """Phân tích chéo dữ liệu Amazon Mỹ (Amazon.com) và từ khóa để chọn Top 15 sản phẩm tốt nhất.
Tiêu chí:
1. Đa dạng phổ giá (Budget, Mid-range, Premium).
2. Ưu tiên có Prime hoặc Rating > 4.2 và số lượng review cực cao (thị trường Mỹ rất quan trọng social proof).
3. THƯƠNG HIỆU RÕ RÀNG: LOẠI BỎ NGAY LẬP TỨC các sản phẩm có tên thương hiệu rác, ký tự vô nghĩa gõ bừa từ bàn phím. CHỈ CHỌN thương hiệu uy tín hoặc tên đọc được dễ dàng bằng tiếng Anh.
4. Tối ưu SEO: Khớp với từ khóa tiếng Anh có Volume cao.

Dữ liệu Amazon: {amazon_data}
Từ khóa: {keywords_json}

YÊU CẦU ĐẦU RA (JSON):
{
    "top_15": [
        {
            "asin": "...", 
            "name": "...", 
            "url": "https://www.amazon.com/dp/...", 
            "price": "...", 
            "rating": "...", 
            "reason": "Lý do chọn bằng tiếng Việt",
            "relevant_keywords": ["english keyword 1", "english keyword 2"] // BẮT BUỘC trích xuất chính xác 2-4 từ khóa từ danh sách cung cấp. Tuyệt đối không tự bịa.
        }
    ]
}"""

P3_TEMPLATE = """Đóng vai Giám khảo chuyên môn. Đọc chi tiết features, giá và review của 15 sản phẩm Amazon Mỹ để chọn ra ĐÚNG 5 SẢN PHẨM XUẤT SẮC NHẤT đưa vào video review.

TIÊU CHÍ LỰA CHỌN BẮT BUỘC (QUAN TRỌNG ĐỂ KHỚP TAG):
1. Phân bổ thứ hạng BẮT BUỘC (Đội hình đa dạng phân khúc): 
   - Vị trí Top 1: [Best Overall] (Sản phẩm toàn diện nhất, rating cao nhất).
   - Vị trí Top 2: [Premium Pick] (Sản phẩm cao cấp, đắt tiền, nhiều tính năng nhất).
   - Vị trí Top 3: [Best Value / Bang for the buck] (Cân bằng giá và hiệu năng tốt nhất).
   - Vị trí Top 4: [Solid Alternative] (Sự lựa chọn thay thế an toàn có điểm nhấn riêng).
   - Vị trí Top 5: [Best Budget] (Sản phẩm rẻ nhất nhưng vẫn dùng tốt).
2. LƯU Ý LOẠI TRỪ KHẮT KHE: Người Mỹ cực kỳ ghét việc bị lừa dối (rip-off). Dựa vào Review Summary, thẳng tay LOẠI BỎ ngay các sản phẩm bị chê tơi tả về việc "ngừng hoạt động sau vài tháng", "Customer service tồi tệ", hoặc lỗi vặt liên tục.
3. ĐA DẠNG THƯƠNG HIỆU: Không để 1 thương hiệu chiếm quá 2 vị trí.

[LUẬT ÉP BUỘC JSON]: 1. Tuyệt đối KHÔNG sử dụng dấu ngoặc kép (") bên trong các đoạn text giải thích (trường 'reasoning'). Nếu cần nhấn mạnh, chỉ dùng dấu nháy đơn ('). 2. TUYỆT ĐỐI KHÔNG XUỐNG DÒNG (Enter) bên trong nội dung của biến 'reasoning'. Toàn bộ giá trị phải nằm trên một dòng duy nhất.

Dữ liệu sản phẩm: {scraped_data}

TRẢ VỀ JSON CHÍNH XÁC THEO CẤU TRÚC:
{
    "top_5_budget": "Mã_ASIN_5",
    "top_4_alternative": "Mã_ASIN_4",
    "top_3_best_value": "Mã_ASIN_3",
    "top_2_premium_pick": "Mã_ASIN_2",
    "top_1_best_overall": "Mã_ASIN_1",
    "reasoning": "Giải thích tóm tắt bằng tiếng Việt lý do phân bổ..."
}"""

P4_TEMPLATE = """# YouTube Script Generation Prompt - USA MARKET

Bạn là một chuyên gia review sản phẩm và tối ưu hóa AEO (AI Search Optimization). Generate a highly engaging, fast-paced, SEO-optimized YouTube script (6-8 minutes) for a TOP 5 product ranking video on Amazon US.

## CRITICAL RULES
- **ABSOLUTELY NO ITALIAN, VIETNAMESE, OR JAPANESE WORDS IN THE SCRIPT OUTPUT.** The output MUST be 100% in American English (except for section tags like <intro>, title:, description: which remain as is).
- **Target Audience:** American consumers (fast attention span, value ROI).
- **TTS Optimization (LUẬT PHÁT ÂM TTS):** The script must be perfectly written for Text-To-Speech (TTS) engines. Spell out symbols naturally (e.g., write "dollars" instead of "$", write "percent" instead of "%"). Use contractions (e.g., "don't", "it's"). Avoid weird special characters.

## INPUT
- **Channel Name (Branding)**: {channel_branding}
- **Host Pronoun/Name**: {host_name}
- **Product Category**: {seed_keywords}
- **Language**: US English (Conversational, dynamic, passionate).
- **Persona**: {selected_persona} (Traits: {persona_traits})
{meme_instruction}
- **Keywords**: {refined_keywords}
- **Tag Candidates**: {tag_candidates_str}
- **Product Data**: {final_5_data}
- **Context**: Year 2026.

## 🎯 SEO, BRANDING & METADATA RULES (CRITICAL)
Bạn phải phân lập rõ ràng 2 quy tắc xử lý từ khóa cho 2 khu vực khác nhau:

[KHU VỰC 1: METADATA - Tiêu đề, Mô tả, Tags]
- BẮT BUỘC giữ nguyên bản 100% cấu trúc từ khóa SEO (Exact Match) trong phần tags. Không tự ý thêm bớt mạo từ.

[KHU VỰC 2: SCRIPT - Lời thoại từ <intro> đến <outro>]
- BRANDING (QUAN TRỌNG): Bắt buộc xưng hô là "{host_name}" và giới thiệu tên kênh là "{channel_branding}" ở phần Intro HOẶC Outro một cách cực kỳ tự nhiên.
- TỪ KHÓA: Lồng ghép từ khóa vào câu thoại dưới dạng từ đồng nghĩa hoặc thêm mạo từ (a, an, the) để câu văn trôi chảy. Tuyệt đối KHÔNG dùng dấu ngoặc kép (" ") cho cụm từ khóa trong lời thoại.

## ⏱️ STRICT WORD LIMITS (NON-NEGOTIABLE)
| Section | Target Words | HARD MAX |
|---------|--------------|----------|
| Hook & Intro | 100-140 | 165 |
| Buying Guide | 155-195 | 220 |
| Products (x5) | ~260 per product | 290 per product |
| Conclusion | 65-90 | 105 |

---
## VIDEO STRUCTURE & LOGIC

### 1. HOOK & INTRO (Tag: <intro>)
- **Hook:** EXTEND curiosity from title. NEVER say "Hey guys, welcome back" first.
- **Retention Bait:** BẮT BUỘC chèn một câu mồi nhử để giữ chân người xem đi qua phần Buying Guide. (e.g., "Number one offers insane value, but before the ranking, here are 3 traps that will waste your money...").

### 2. BUYING GUIDE (Tag: <buying_guide>)
- Provide 3 Essential Tips dưới dạng "Tránh những cạm bẫy" (The Classic Trap, Spec Sheet Lie) để đánh vào tâm lý người Mỹ.
- **The Bridge:** Ở tip số 3, BẮT BUỘC BẮC CẦU sang Top 5. (e.g., "Third: [Tiêu chí]. Don't worry, every product on my Top 5 passes this test perfectly. Alright, enough talking, let's kick things off with number 5.")

### 3. PRODUCT REVIEWS (<top5> to <top1>)
- **The 'Best For' Label:** Bắt đầu review mỗi sản phẩm bằng một định vị rõ ràng (Ví dụ: "Kicking things off at number 5, the [Product] is the absolute best choice if you..."). KHÔNG lặp lại một cấu trúc mở đầu cho cả 5 sản phẩm.
- **SPEC-STORY FUSION:** Weave specs WITH real user experiences (e.g., "5000 mAh battery... one guy took this on a 3-day hike"). 
- **Limitation + Solution:** Be DIRECT. Name a minor flaw, quantify it, give workaround.

### 4. 🎭 TTS EMOTION TAGS
Insert exact emotion tags in brackets to control the TTS tone naturally: `[laugh]`, `[sigh]`, `[gasp]`, `[excited]`, `[pause]`. (Use 1-2 tags max per product section).

---
## OUTPUT FORMAT (MANDATORY EXACT STRUCTURE)

title:
[MUST contain the main SEO keyword. Format: [Keyword] - [Hook] - 2026]

description:
Disclaimer: This description contains affiliate links. If you purchase through these links, you support the channel at no additional cost. Thank you!

[2-3 introductory sentences in English containing primary keywords]

#5. [Brand + Product Name]
- Why we recommend it: [1-2 sentences summarizing in English]
👉 Amazon Link: {LINK_5}

#4. [Brand + Product Name]
- Why we recommend it: [1-2 sentences summarizing in English]
👉 Amazon Link: {LINK_4}

#3. [Brand + Product Name]
- Why we recommend it: [1-2 sentences summarizing in English]
👉 Amazon Link: {LINK_3}

#2. [Brand + Product Name]
- Why we recommend it: [1-2 sentences summarizing in English]
👉 Amazon Link: {LINK_2}

#1. [Brand + Product Name]
- Why we recommend it: [1-2 sentences summarizing in English]
👉 Amazon Link: {LINK_1}

[Outro & Call to action in English]
Hashtags: [3-5 hashtags in English]

tags: 
[Comma-separated English keywords. Max 460 chars]

script:
<intro>
[English content - MUST MENTION CHANNEL NAME "{channel_branding}"]

<buying_guide>
[English content - MUST include The Bridge transition]

<top5>
[English content - Use emotion tags]

<top4>
[English content - Use emotion tags]

<top3>
[English content - Use emotion tags]

<top2>
[English content - Use emotion tags]

<top1>
[English content - Use emotion tags]

<outro>
[English content - Call to action & Mention "{host_name}"]
"""

# --- HÀM HỖ TRỢ CHUNG ---
def clean_and_parse_json(ai_text):
    text = ai_text.strip()
    text = re.sub(r'^```(json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        if start != -1:
            stack = 0
            for i in range(start, len(text)):
                if text[i] == '{': stack += 1
                elif text[i] == '}':
                    stack -= 1
                    if stack == 0:
                        try: return json.loads(text[start:i+1])
                        except: break
        raise ValueError(f"Lỗi bóc tách JSON.")

def call_gemini_with_retry(contents, response_mime_type=None, max_retries=3, target_model=MODEL_ID):
    delay = 3
    for attempt in range(max_retries):
        try:
            if response_mime_type:
                return client.models.generate_content(
                    model=target_model, contents=contents, 
                    config=types.GenerateContentConfig(response_mime_type=response_mime_type)
                )
            return client.models.generate_content(model=target_model, contents=contents)
        except Exception as e:
            if "503" in str(e) or "429" in str(e) or "quota" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else: raise e
            else: raise e

# --- HÀM XỬ LÝ DỮ LIỆU ---
def parse_amazon_md_search(md_texts):
    """Đọc file MD của trang kết quả tìm kiếm (Amazon.com)"""
    products = []
    seen_asins = set()
    for text in md_texts:
        blocks = text.split('## Product')
        for block in blocks[1:]:
            title_match = re.search(r'\*\*Title\*\*: (.*)', block)
            asin_match = re.search(r'\*\*ASIN\*\*: (.*)', block)
            if title_match and asin_match:
                title = title_match.group(1).strip()
                # TỐI ƯU MỸ: Lọc bỏ chữ "Sponsored" ở các sp quảng cáo thay vì tiếng Ý
                title = re.sub(r'^Sponsored\s*[-–]\s*', '', title, flags=re.IGNORECASE)
                
                asin = asin_match.group(1).strip()
                if asin not in seen_asins:
                    products.append({
                        "asin": asin, "name": title,
                        "url": f"https://www.amazon.com/dp/{asin}" 
                    })
                    seen_asins.add(asin)
    return products

def clean_md_content(text):
    """Lọc rác siêu chuẩn cho Amazon USA Markdown"""
    # Xóa khối Chính sách bảo hành & Trả hàng của Mỹ
    text = re.sub(r'### Returns & Refunds.*?Marketplace items\.', '', text, flags=re.DOTALL|re.IGNORECASE)
    # Xóa khối Feedback báo cáo giá thấp hơn
    text = re.sub(r'### Feedback\nWould you like to \*\*tell us about a lower price\?\).*?Sign in to provide feedback\.', '', text, flags=re.DOTALL|re.IGNORECASE)
    # Xóa metadata rác cuối file
    text = re.sub(r'## Scraped Information.*', '', text, flags=re.DOTALL)
    # Xóa khoảng trắng thừa
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def parse_detailed_md_files(md_contents_list):
    scraped_data = []
    for md_text in md_contents_list:
        try:
            cleaned_text = clean_md_content(md_text)
            
            asin_match = re.search(r'\*\*ASIN\*\*: (.*?)\n', cleaned_text)
            title_match = re.search(r'# (.*?)\n', cleaned_text)
            price_match = re.search(r'\*\*Price\*\*: (.*?)\n', cleaned_text)
            rating_match = re.search(r'\*\*Rating\*\*: (.*?)\n', cleaned_text)
            
            asin = asin_match.group(1).strip() if asin_match else "UNKNOWN"
            title = title_match.group(1).strip() if title_match else "UNKNOWN"
            
            valuable_parts = []
            target_sections = [
                "## Basic Information", 
                "## Key Features", 
                "## Specifications", 
                "## Customer Review Summary", 
                "## Review Aspects"
            ]
            for section in target_sections:
                pattern = rf"{section}(.*?)(?=\n## |\Z)"
                match = re.search(pattern, cleaned_text, re.DOTALL)
                if match:
                    valuable_parts.append(f"{section}\n{match.group(1).strip()}")
            
            final_description = "\n\n".join(valuable_parts)
            
            images = []
            img_section = re.search(r'## Description Image Links\n(.*?)(?=\n## |\Z)', cleaned_text, re.DOTALL)
            if img_section:
                images = re.findall(r'- (https://m\.media-amazon\.com[^\s]+)', img_section.group(1))
            
            scraped_data.append({
                "asin": asin,
                "name": title,
                "url": f"https://www.amazon.com/dp/{asin}",
                "price": re.sub(r'~~.*?~~', '', price_match.group(1)).strip() if price_match else "N/A",
                "rating": rating_match.group(1).strip() if rating_match else "N/A",
                "description": final_description,
                "full_text_length": len(final_description),
                "images": images
            })
        except Exception as e:
            st.error(f"Lỗi đọc file MD: {e}")
    return scraped_data

def process_single_ocr(item):
    TEXT_THRESHOLD = 800 
    
    if item['full_text_length'] < TEXT_THRESHOLD:
        st.write(f"🔍 Sản phẩm {item['asin']} có mô tả mỏng. Đang chạy OCR...")
        
        ocr_prompt = """You are an advanced OCR system.
Task: Extract technical specifications, key features, and main selling points from the product images.
RULES:
1. OUTPUT MUST BE 100% IN ENGLISH.
2. Use a short, concise bulleted list. NO additional explanations."""
        
        if 'images' in item and len(item['images']) > 0:
            gemini_contents = [ocr_prompt]
            target_images = item['images'][:5]
            has_valid_image = False
            
            for img_url in target_images:
                try:
                    res = requests.get(img_url, timeout=10)
                    if res.status_code == 200:
                        img = Image.open(io.BytesIO(res.content))
                        if img.mode != 'RGB': img = img.convert('RGB')
                        gemini_contents.append(img)
                        has_valid_image = True
                except: pass
            
            if has_valid_image:
                try:
                    ocr_result = call_gemini_with_retry(gemini_contents).text
                    item['description'] += "\n\n[ADDITIONAL DATA FROM OCR IMAGES]:\n" + ocr_result
                except Exception as e:
                    st.warning(f"Không thể OCR cho {item['asin']}: {e}")
    return item

# --- GIAO DIỆN CHÍNH ---
st.title("🛠️ Hệ Thống Kịch Bản Amazon USA (Eagle Eye Edition 🇺🇸)")

with st.sidebar:
    st.header("Cài Đặt Đầu Vào")
    seed_keywords = st.text_input("Từ khóa ngách (Tiếng Anh):", "coffee maker")
    selected_persona = st.selectbox("Chọn Persona Review (Phong cách Mỹ):", list(PERSONA_DICT.keys()))
    specific_theme = st.text_input("Định hướng ngách cụ thể (Tùy chọn):", placeholder="VD: For college students, minimalist setup...")
    trending_memes = st.text_input("🔥 Trend/Meme đang hot (Bỏ trống AI tự bốc):", placeholder="VD: game changer, absolute beast...")
    
    st.divider()
    st.subheader("Cấu hình Thương Hiệu (Branding)")
    channel_branding = st.text_input("Tên Kênh YouTube:", value="Tech Selected")
    host_name = st.text_input("Cách xưng hô (VD: I, we, tên host):", value="I")

tab1, tab2 = st.tabs(["📌 BƯỚC 1: Lọc 15 Sản Phẩm US", "✍️ BƯỚC 2: OCR & Viết Kịch Bản US"])

# ==========================================
# GIAI ĐOẠN 1
# ==========================================
with tab1:
    st.header("Cung cấp tệp tìm kiếm thô (Amazon.com)")
    col1, col2 = st.columns(2)
    with col1:
        vidiq_files = st.file_uploader("1. Tệp Từ khóa VidIQ (.CSV)", type="csv", accept_multiple_files=True)
    with col2:
        md_files_search = st.file_uploader("2. Tệp Kết quả Amazon (.MD)", type="md", accept_multiple_files=True)
        
    if st.button("🚀 Xử lý Bước 1", type="primary"):
        if not vidiq_files or not md_files_search:
            st.warning("Vui lòng upload đủ file CSV và MD Tìm kiếm!")
            st.stop()
            
        with st.status("Đang phân tích Bước 1..."):
            dfs = []
            for file in vidiq_files:
                df_temp = pd.read_csv(file, sep=',', quotechar='"', on_bad_lines='skip')
                col_kw = next((c for c in df_temp.columns if 'keyword' in c.lower() or 'từ khóa' in c.lower()), None)
                col_vol = next((c for c in df_temp.columns if 'volume' in c.lower() or 'search' in c.lower()), None)
                if col_kw and col_vol:
                    df_temp = df_temp[[col_kw, col_vol]].dropna()
                    df_temp.columns = ['Keyword', 'Volume']
                    dfs.append(df_temp)
            vidiq_df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=['Keyword'])
            csv_data = vidiq_df.to_csv(index=False)
            
            md_texts = [f.getvalue().decode("utf-8", errors="ignore") for f in md_files_search]
            amazon_raw_data = parse_amazon_md_search(md_texts)
            
            st.write("Đang lọc Keyword tiếng Anh (US)...")
            prompt1 = P1_TEMPLATE.replace("{csv_data}", csv_data).replace("{seed_keywords}", seed_keywords)
            res1 = call_gemini_with_retry(prompt1, response_mime_type="application/json")
            keywords_json = clean_and_parse_json(res1.text)
            
            st.write("Đang chọn Top 15 USA...")
            prompt2 = P2_TEMPLATE.replace("{amazon_data}", json.dumps(amazon_raw_data, ensure_ascii=False)).replace("{keywords_json}", json.dumps(keywords_json, ensure_ascii=False))
            if specific_theme.strip():
                prompt2 += f"\n\nLƯU Ý: Hãy ưu tiên tìm các sản phẩm phù hợp nhất với chủ đề/ngách sau: '{specific_theme}'."
            res2 = call_gemini_with_retry(prompt2, response_mime_type="application/json")
            top_15_json = clean_and_parse_json(res2.text)
            
            st.session_state['saved_keywords'] = keywords_json
            st.session_state['top_15_json'] = top_15_json
            
        st.success("✅ Đã chốt danh sách 15 sản phẩm tối ưu cho MỸ! Copy link mở tab lấy MD chi tiết.")
        st.markdown("### 🎯 DANH SÁCH 15 LINK:")
        items_list = top_15_json.get('top_15', []) if isinstance(top_15_json, dict) else top_15_json
        for item in items_list:
            url = item.get('url', '')
            asin = item.get('asin', 'UNKNOWN')
            if url:
                html_link = f'👉 **{asin}**: <a href="{url}" target="_blank">{url}</a>'
                st.markdown(html_link, unsafe_allow_html=True)
            else:
                st.write(f"👉 **{asin}**: Không có URL")

# ==========================================
# GIAI ĐOẠN 2
# ==========================================
with tab2:
    st.header("Xử lý 15 sản phẩm chi tiết")
    detailed_md_files = st.file_uploader("Upload 15 file .MD chi tiết", type="md", accept_multiple_files=True)
    
    if st.button("✨ Chốt Top 5 & Xuất Kịch Bản Tiếng Anh (US)", type="primary"):
        if not detailed_md_files:
            st.warning("Vui lòng upload file MD chi tiết!")
            st.stop()
        if 'saved_keywords' not in st.session_state or 'top_15_json' not in st.session_state:
            st.error("Dữ liệu trống. Vui lòng chạy lại BƯỚC 1 trước!")
            st.stop()
            
        with st.status("Đang phân tích và viết kịch bản phong cách Mỹ..."):
            md_contents = [f.getvalue().decode("utf-8", errors="ignore") for f in detailed_md_files]
            scraped_details = parse_detailed_md_files(md_contents)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                scraped_details = list(executor.map(process_single_ocr, scraped_details))
                
            st.write("Giám khảo AI chấm điểm Top 5...")
            prompt3 = P3_TEMPLATE.replace("{scraped_data}", json.dumps(scraped_details, ensure_ascii=False))
            if specific_theme.strip():
                prompt3 += f"\n\nLƯU Ý TỪ ĐẠO DIỄN: Tiêu chí cốt lõi để chọn Top 5 là bám sát chủ đề: '{specific_theme}'."
            res3 = call_gemini_with_retry(prompt3, response_mime_type="application/json", target_model=PRO_MODEL_ID)
            top5_decision = clean_and_parse_json(res3.text)
            
            if isinstance(top5_decision, list): top5_decision = top5_decision[0]
            
            # GẮN TAG KHÓA CHẶT TỪ TOP 5 ĐẾN TOP 1 (KHÔNG BAO GIỜ BỊ ĐẢO NGƯỢC)
            selected_asins = [
                top5_decision.get('top_5_budget'), 
                top5_decision.get('top_4_alternative'),
                top5_decision.get('top_3_best_value'), 
                top5_decision.get('top_2_premium_pick'),
                top5_decision.get('top_1_best_overall')
            ]
            selected_asins = [asin for asin in selected_asins if asin]
            
            final_5_data = []
            rank_labels = ["Top 5", "Top 4", "Top 3", "Top 2", "Top 1"]
            for idx, asin in enumerate(selected_asins):
                for item in scraped_details:
                    if item['asin'] == asin:
                        item_copy = item.copy()
                        item_copy['ASSIGNED_RANK'] = rank_labels[idx]
                        final_5_data.append(item_copy)
                        break
            
            matched_keywords = set()
            top_15_json = st.session_state.get('top_15_json', [])
            items_list = top_15_json.get('top_15', []) if isinstance(top_15_json, dict) else top_15_json
            for item in items_list:
                if item.get('asin') in selected_asins:
                    for kw in item.get('relevant_keywords', []): matched_keywords.add(kw.strip().lower())
            
            keywords_json = st.session_state['saved_keywords']
            original_kws_dict = { kw['keyword'].strip().lower(): kw for kw in keywords_json.get('keywords', []) }
            
            valid_final_keywords = [original_kws_dict[kw] for kw in matched_keywords if kw in original_kws_dict]
            valid_final_keywords = sorted(valid_final_keywords, key=lambda x: int(str(x.get('volume', 0)).replace(',', '').strip() or 0), reverse=True)
            seo_keywords_str = ", ".join([item['keyword'] for item in valid_final_keywords[:15]])
            
            st.write("Đang viết Script (Tối ưu cho luồng TTS Automation)...")
            
            valid_tag_candidates = []
            for kw in keywords_json.get('keywords', []):
                vol_str = str(kw.get('volume', '0')).replace(',', '').strip()
                if vol_str == '<750': continue
                try:
                    if int(vol_str) >= 750:
                        valid_tag_candidates.append(kw['keyword'])
                except: pass
            tag_candidates_str = ", ".join(valid_tag_candidates)
            
            if trending_memes.strip():
                meme_instruction = f"- **Mandatory Expressions**: Naturally insert these phrases into the script: {trending_memes}"
            else:
                meme_list_str = " | ".join(MEME_VAULT)
                meme_instruction = f"- **US Meme/Slang Vault**: To make the script authentic, CHOOSE 2 OR 3 of these expressions and use them naturally: [{meme_list_str}]."
            
            prompt4 = P4_TEMPLATE.replace(
                "{final_5_data}", json.dumps(final_5_data, ensure_ascii=False)
            ).replace("{refined_keywords}", seo_keywords_str)\
             .replace("{tag_candidates_str}", tag_candidates_str)\
             .replace("{seed_keywords}", seed_keywords)\
             .replace("{selected_persona}", selected_persona)\
             .replace("{persona_traits}", PERSONA_DICT[selected_persona])\
             .replace("{meme_instruction}", meme_instruction)\
             .replace("{channel_branding}", channel_branding)\
             .replace("{host_name}", host_name)
            
            if specific_theme.strip():
                theme_instruction = f"- **Target Niche/Theme**: {specific_theme}\n[CONTENT DIRECTION]: Focus heavily on the needs of the '{specific_theme}' audience."
                prompt4 = prompt4.replace("## INPUT", f"## INPUT\n{theme_instruction}")

            res4 = call_gemini_with_retry(prompt4, target_model=PRO_MODEL_ID)
            main_script = res4.text
            
            for item in final_5_data:
                rank_label = item.get('ASSIGNED_RANK', '') 
                if rank_label:
                    rank_num = rank_label.replace('Top ', '').strip() 
                    placeholder = f"{{LINK_{rank_num}}}"
                    main_script = main_script.replace(placeholder, item.get('url', ''))

        st.success("🎉 Hoàn tất Kịch bản tiếng Anh (US)! (Let's go!)")
        st.text_area("Kịch Bản Hoàn Chỉnh (English)", value=main_script, height=600)
        
        with st.expander("🔍 Xem dữ liệu Debug (Top 5 & OCR)"):
            st.json(final_5_data)
