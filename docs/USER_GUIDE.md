# 📱 IntegrityBot — Foydalanuvchi Qo'llanmasi (Telegram Bot)

**Versiya:** 1.0  
**Sana:** 2026-yil 2-mart  
**Maqsad:** Telegram bot orqali murojaat yuborishni o'rganish

---

## 📋 MUNDARIJA

1. [Botni Boshlash](#1-botni-boshlash)
2. [Murojaat Yuborish](#2-murojaat-yuborish)
3. [Anonimlik Haqida](#3-anonimlik-haqida)
4. [Murojaatni Kuzatish](#4-murojaatni-kuzatish)
5. [Admin bilan Muloqot](#5-admin-bilan-muloqot)
6. [Mening Murojaatlarim](#6-mening-murojaatlarim)
7. [Sozlamalar](#7-sozlamalar)
8. [Tez-tez So'raladigan Savollar](#8-tez-tez-soraladigan-savollar)
9. [Huquqlaringiz](#9-huquqlaringiz)

---

## 1. Botni Boshlash

### 1.1 Botni Topish

Telegram qidiruvida bot nomini yozing yoki to'g'ridan-to'g'ri havolaga o'ting:
```
@IntegrityBot (misol)
```

### 1.2 /start Buyrug'i

Botni birinchi marta ishga tushirish:
1. Telegram'da botni oching
2. `/start` yozing yoki **"Start"** tugmasini bosing
3. Xush kelibsiz xabari va asosiy menyu paydo bo'ladi

### 1.3 Asosiy Menyu

Bot quyidagi tugmalarni ko'rsatadi:

```
┌─────────────────────────────────┐
│  📝 Murojaat yuborish           │
│  📋 Mening murojaatlarim        │
│  ❓ FAQ / Savol-javoblar        │
│  📞 Aloqa                       │
│  ⚙️ Sozlamalar                  │
└─────────────────────────────────┘
```

---

## 2. Murojaat Yuborish

### 2.1 Bosqichlar

**📝 Murojaat yuborish** tugmasini bosing va quyidagi bosqichlarni bajaring:

#### Bosqich 1: Kategoriya Tanlash
```
Murojaat kategoriyasini tanlang:

🔴 Korrupsiya / Pora
⚖️ Manfaatlar to'qnashuvi
💸 Firibgarlik / O'g'irlik
⚠️ Xavfsizlik buzilishi
🚫 Kamsitish / Bezovtalik
📋 Tender buzilishi
❓ Boshqa
```

Tegishli kategoriyani bosing.

#### Bosqich 2: Tavsif Yozish

Voqeaning batafsil tavsifini yozing:
- Qachon va qayerda yuz bergan
- Kim ishtirok etgan (ixtiyoriy)
- Nima bo'lganligi

> 💡 **Maslahat:** Qancha ko'p ma'lumot bersangiz, shuncha tez ko'rib chiqiladi.

#### Bosqich 3: Fayl Biriktirish (Ixtiyoriy)

```
📎 Fayl biriktirmoqchimisiz?

✅ Ha, fayl yuboraman
⏭️ Yo'q, o'tkazib yuboraman
```

Fayl yuborishni tanласangиз:
- Rasm, hujjat, video yuboring (max 20 MB, 5 tagacha)
- Botga faylni to'g'ridan-to'g'ri yuboring
- **"Tugatdim"** tugmasini bosing

**Qabul qilinadigan formatlar:**
| Tur | Formatlar |
|-----|-----------|
| Rasm | JPG, PNG, GIF, WebP |
| Hujjat | PDF, Word, Excel |
| Video | MP4, AVI, MOV |
| Audio | MP3, WAV |
| Arxiv | ZIP, RAR |

#### Bosqich 4: Anonimlik Tanlash

```
Murojaat qanday yuborilsin?

🔒 Anonim (ismim ko'rinmasin)
👤 Nomimni ko'rsatish
```

> 🔒 **Tavsiya:** Xavfsizligingiz uchun anonim yuborishni tavsiya qilamiz.

#### Bosqich 5: Tasdiqlash

Barcha ma'lumotlarni ko'rib chiqing va **"✅ Yuborish"** tugmasini bosing.

### 2.2 Muvaffaqiyatli Yuborilgandan Keyin

```
✅ Murojaatingiz muvaffaqiyatli qabul qilindi!

📋 Murojaat raqami: CASE-20260302-00001
⏰ Ko'rib chiqish muddati: 3 ish kuni

Bu raqamni saqlang — holat tekshirish uchun kerak bo'ladi.
```

> ⚠️ **DIQQAT:** Murojaat raqamini albatta saqlab qo'ying!

---

## 3. Anonimlik Haqida

### 3.1 Anonimlik Kafolati

Anonim yuborishni tanlasangiz:

- ✅ Ismingiz **hech qachon** saqlanmaydi
- ✅ Telefon raqamingiz **saqlanmaydi**
- ✅ IP manzilingiz murojaatga **biriktirilmaydi**
- ✅ Telegram user ID'ngiz **shifrlanadi**

### 3.2 Texnik Himoya

- Barcha ma'lumotlar **AES-256-GCM** shifrlash bilan saqlanadi
- Ma'lumotlar bazasiga kirish uchun **maxsus ruxsat** kerak
- Barcha harakatlar **audit log**da qayd etiladi

### 3.3 Anonimlik Chegaralari

Anonimlik **ta'minlanmagan** holatlar:
- ❌ Agar tavsifingizda o'zingiz haqingizda ma'lumot bergan bo'lsangiz
- ❌ Agar telegram akkauntingiz shaxsiy ma'lumotlaringizni ko'rsatsa va anonim emas deb tanlasangiz

---

## 4. Murojaatni Kuzatish

### 4.1 Holat Tekshirish

**📋 Mening murojaatlarim** → murojaat raqamini kiriting

yoki

```
/status CASE-20260302-00001
```

### 4.2 Holat Ma'nolari

| Holat | Tavsif |
|-------|--------|
| 🔵 **Yangi** | Qabul qilindi, hali ko'rib chiqilmagan |
| 🟡 **Ko'rib chiqilmoqda** | Responsible xodim ishlayapti |
| 🟠 **Ma'lumot kerak** | Sizdan qo'shimcha ma'lumot so'ralmoqda |
| 🟢 **Yakunlandi** | Muammo hal qilindi |
| 🔴 **Rad etildi** | Asossiz topildi yoki jurisdiktsiyamizdan tashqarida |

### 4.3 Eslatmalar

24 soat ichida javob kelmasa, bot avtomatik ravishda eslatma yuboradi.

---

## 5. Admin bilan Muloqot

### 5.1 Javob Olish

Admin javob yozganida bot sizga xabar yuboradi:

```
📬 Murojaat CASE-20260302-00001 bo'yicha javob keldi
──────────────────────────────
Murojaatingizni ko'rib chiqdik va...

_Compliance departamenti_
```

### 5.2 Qo'shimcha Ma'lumot Yuborish

Agar admin ma'lumot so'rasa:

1. Bot xabariga javob yozing
2. **"Javob yuborish"** tugmasini bosing
3. Yoki yangi fayl biriktiring

### 5.3 Anonim Muloqot

Anonim murojaat yuborgan bo'lsangiz ham admin bilan muloqot mumkin — **shaxsiyatingiz oshkor bo'lmaydi**. Bot token orqali xabarlarni yetkazib beradi.

---

## 6. Mening Murojaatlarim

**📋 Mening murojaatlarim** bo'limida:

- Barcha yuborgan murojaatlaringiz ro'yxati
- Har birining joriy holati
- Oxirgi yangilanish sanasi
- Javoblar tarixi

---

## 7. Sozlamalar

**⚙️ Sozlamalar** bo'limida:

| Sozlama | Tavsif |
|---------|--------|
| 🌐 Til | O'zbek / Rus / Ingliz |
| 🔔 Bildirishnomalar | Yoqish/o'chirish |
| 📱 Aloqa ma'lumotlari | Eslatmalar uchun |

---

## 8. Tez-tez So'raladigan Savollar

**❓ Murojaat yuborish xavfsizmi?**  
Ha. Barcha ma'lumotlar shifrlangan holda saqlanadi. Anonim tanlaganingizda hech qanday shaxsiy ma'lumot saqlanmaydi.

**❓ Murojaat raqamini yo'qotib qo'ydim. Nima qilaman?**  
Botda **"📋 Mening murojaatlarim"** bo'limini oching — barcha murojaatlaringiz ro'yxati mavjud.

**❓ Murojaatim qachon ko'rib chiqiladi?**  
Standart muddat: **3 ish kuni**. Kritik murojaatlar — **24 soat** ichida.

**❓ Fayl yuklab bo'lmayapti. Nima qilaman?**  
- Fayl hajmi 20 MB dan oshmasligi kerak
- Format qo'llab-quvvatlanishi kerak (.exe, .bat kabi fayllar qabul qilinmaydi)

**❓ Javob kelmayapti.**  
- 24 soat kutib ko'ring
- Bot eslatma yuboradi
- Holat tekshiring: `/status CASE-XXXXXXXX-XXXXX`

**❓ Murojaatimni bekor qila olamanmi?**  
Yuborilgan murojaatni bekor qilib bo'lmaydi, lekin izoh orqali qo'shimcha ma'lumot berishingiz mumkin.

**❓ Bir nechta fayl yuborishim mumkinmi?**  
Ha, bitta murojaatga maksimal **5 ta** fayl biriktirishingiz mumkin.

**❓ So'rovnomalarda ishtirok eta olamanmi?**  
Ha, bot guruh/kanalga so'rovnoma yuborganida to'g'ridan-to'g'ri ovoz bera olasiz.

---

## 9. Huquqlaringiz

### 9.1 Ma'lumotlaringizni Himoya Qilish

Siz quyidagi huquqlarga egasiz:
- ✅ Murojaatingiz holati bilan tanishish
- ✅ Qo'shimcha ma'lumot berish
- ✅ Javob olish huquqi

### 9.2 Maxfiylik

Compliance departamenti:
- Siz yuborgan ma'lumotlarni **faqat murojaat ko'rib chiqish** uchun ishlatadi
- Ma'lumotlaringizni uchinchi tomonlarga **bermaydi** (qonun talab qilgan hollar bundan mustasno)
- Barcha ma'lumotlar **3-5 yildan** keyin to'liq o'chiriladi

### 9.3 Anonim Murojaatchi Himoyasi

Kompaniya siyosatiga ko'ra:
- Murojaat yuborganlarga **tazyiq ko'rsatish taqiqlanadi**
- Shaxsiyatni aniqlashga **urinish taqiqlanadi**
- Qasos olish harakati **intizomiy jazoga** sabab bo'ladi

---

## 📞 Qo'llab-Quvvatlash

Texnik muammo bo'lsa:
- Bot'da `/help` yozing
- Compliance departamentiga murojaat qiling

---

*Hujjat versiyasi: 1.0 | 2026-yil 2-mart*

