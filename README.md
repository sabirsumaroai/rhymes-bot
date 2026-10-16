# Rangeela Rhymes Bot — setup guide (sab free)

Ye bot roz apne aap: original Hindi+English rhyme likhta hai → awaaz banata hai → cartoon images banata hai → 6-8 minute ka video + ek Short + 2 thumbnails banata hai → tumhe **Telegram** par bhej deta hai. Upload **tum khud** YouTube Studio se karte ho (isse API ka private-lock aur audit ka jhanjhat nahi hai).

---

## Part A — Ek baar ka setup (lagbhag 30-40 minute)

### Step 1: GitHub account aur repo
1. github.com par free account banao.
2. Upar `+` → **New repository** → naam `rhymes-bot` → **Public** chuno → **Create repository**.
   (Public isliye ki GitHub Actions public repo me free hai.)
3. Is zip ko computer par extract karo. Repo page par **uploading an existing file** link dabao aur extract hui **saari files aur folders** (khaas kar `.github` folder) drag-drop karo → **Commit changes**.
   - Agar `.github` folder upload na ho (hidden folder hota hai): **Add file → Create new file** me naam likho `.github/workflows/daily.yml`, file ka content paste karo. Aise hi `weekly.yml` aur `voice.yml` bhi.

### Step 2: Gemini key (script ke liye)
1. aistudio.google.com par Google account se login → **Get API key** → **Create API key**.
2. Key copy karke rakh lo.

### Step 3: Telegram bot (video yahin aayega)
1. Telegram me **@BotFather** kholo → `/newbot` → naam do → **token** milega (`123456:ABC...`). Copy karo.
2. Apne naye bot ko search karke kholo aur **Start** dabao, phir `hi` likho.
3. Browser me ye link kholo (TOKEN ki jagah apna token): `https://api.telegram.org/botTOKEN/getUpdates`
4. Jawab me `"chat":{"id":123456789` dhundo. Ye number tumhara **chat id** hai.

### Step 4: Secrets daalo
Repo → **Settings → Secrets and variables → Actions → New repository secret**. Ek ek karke banao:

| Secret ka naam | Kya daalna hai | Zaroori? |
|---|---|---|
| `GEMINI_API_KEY` | Step 2 wali key | Haan |
| `TELEGRAM_BOT_TOKEN` | Step 3 ka token | Haan |
| `TELEGRAM_CHAT_ID` | Step 3 ka chat id | Haan |
| `GROQ_API_KEY` | console.groq.com par free account → API key | **Bahut zaroori mana jaaye** (Gemini ki limit ho to backup) |
| `POLLINATIONS_KEY` | enter.pollinations.ai par free signup → key | Achha rahega (images tez aur bina watermark ke; bina key ke har 15 sec me 1 image) |
| `OPENROUTER_API_KEY` | openrouter.ai free key | Optional (doosra backup) |
| `YT_API_KEY` | Google Cloud Console → naya project → **YouTube Data API v3** enable → Credentials → API key | Optional (weekly trend report ke liye) |
| `YT_CHANNEL_ID` | Studio → Settings → Channel → Advanced settings me "Channel ID" | Optional |

### Step 5: Apna channel naam / characters set karo
Repo me `config.json` kholo → pencil icon:
- `channel_name`: apne channel ka naam.
- `characters`: **apne original characters** (kisi existing show jaise nahi). Jaise diye hain waise ek line me look likho.
- `topics`: pasand ke topic. Khatam hone par Gemini khud naye sochta hai.
→ **Commit changes**.

### Step 6: Pehli baar chalao (hafte ka stock)
1. Repo me **Actions** tab. Agar "workflows enable" ka button dikhe to dabao.
2. Left me **daily-video** → **Run workflow** → `count` me **7** likho → **Run workflow**.
3. Pehle run me kuch ghante lag sakte hain (har video ~15-30 min). Har video banne par Telegram par aayega.
   Bas — ab ye roz subah **8:00 baje (IST)** apne aap 1 naya video banayega.

---

## Part B — Roz / hafte ka kaam (tumhara kaam, 5-10 minute)

Telegram par har video ke saath aata hai: 2 thumbnails, preview video, title/description/tags, lyrics, aur **download links** (master video + Short).

Hafte me ek baar (best) ya roz:
1. Preview dekho. Theek na lage to upload mat karo.
2. Master video ka link kholo → download.
3. YouTube Studio → **Create → Upload videos**.
4. **"Made for kids" = Yes** chuno (ye zaroori hai).
5. Title, description, tags paste karo. Thumbnail A ya B lagao (dono try karke dekho kaunsa chalta hai).
6. **Visibility → Schedule** se date/time lagao. 7 video ek baar me schedule kar do, to roz upload karne ki zaroorat nahi.
7. Short ko bhi alag se upload karo (Shorts).

## Part C — Behtar views ke liye (jo humne 8 points me tay kiya)

| Point | Bot me kahan hai |
|---|---|
| 1. Pehle 30 sec me hook | Script ka pehla scene chorus hota hai, koi intro/greeting nahi |
| 2. Thumbnail + title | 2 thumbnails (A: peela text, B: laal patti), 3 title options |
| 3. Kam bhari jagah | Hindi+English mix; `config.json` me topics badal sakte ho (Marwari/Rajasthani jaisi bhasha me gaane ke liye prompt me `topics` badlo) |
| 4. Ek hi character baar-baar | `characters` har image prompt me jaata hai |
| 5. Insaani awaaz | Neeche "Apni awaaz" dekho |
| 6. Short | Har video ke saath ~40 sec ka vertical Short |
| 7. Dekho, seekho, dohrao | Weekly report + `feedback.txt` |
| 8. Sabr | Roz/lagatar upload; naye channel ko 3-6 mahine lag sakte hain |

### Apni awaaz lagana (sabse bada fark)
1. Telegram message ka **lyrics** wala hissa padho/gaao aur phone ke voice recorder me record karo (saare lyrics, jis order me likhe hain).
2. File ka naam **video ID** rakho (message me "NAYA VIDEO READY: <ID>"), jaise `20261017-001-chintu.m4a`.
3. GitHub repo → `my_voice` folder → **Add file → Upload files** → file daalo → Commit.
4. Kuch minute me Telegram par "-voice" wala naya video aayega. (Awaaz ke hisaab se scenes lagbhag sync hote hain, har shabd ke saath exact nahi. Video ki lambai tumhari recording jitni hogi.)

### Background music
`music/` folder me sirf wahi mp3 daalo jinka license commercial use allow karta ho (YouTube Audio Library ya CC0). Bot unhe halke volume par mix karega. Na daalo to bina music ke banega.

### Weekly report aur feedback
- Har Ravivar 9 baje Telegram par report aati hai: tumhare video ka haal + 7 naye original idea. Ye idea agle hafte automation khud use karta hai.
- Studio → Analytics me **CTR** aur **Average view duration** dekho. Jo chala/nahi chala, `feedback.txt` me 1 line likh do (jaise `counting wale gaane chale, lullaby nahi`). Agli script usi hisaab se banegi.

---

## Part D — Ye kabhi na rukne ke liye kya lagaya hai

- **Script:** Gemini ke 3 models → Groq → OpenRouter. Limit (429) aaye to wait karke retry, phir agla.
- **Images:** Pollinations → purani cached images → bina internet ki simple art. (Kam quality ho to Telegram message me ⚠️ chetavni aati hai.)
- **Awaaz:** edge-tts → gTTS → espeak.
- **Din chhoot jaye** (sab fail): agli baar apne aap extra video banata hai (max 3) aur Telegram par alert bhejta hai.
- **Fail alert:** Telegram message + GitHub email.
- **60 din wala rule:** roz state commit hota hai aur workflows khud ko re-enable bhi karte hain.
- **Copyright safety:** blocked words ki list (`blocked_terms`) me bade kids channels/rhymes ke naam hain; script me aaye to reject hoti hai.

## Part E — Zaroori sachchaiyan (padh lo)

- 100% fail-proof nahi hota. Free services kabhi bhi badal/band ho sakti hain. Isliye buffer (hafte ka stock) aur alert rakhe hain.
- **Made-for-Kids + AI** content par YouTube sabse sakht hai. Monetization milne ki guarantee nahi (RPM bhi kam). Isse experiment ki tarah chalao.
- Policy channel-level par lagti hai. Roz bilkul ek jaise video mat daalo; `topics`, `formats` aur `feedback.txt` se variety rakho, aur thoda insaani touch (apni awaaz) daalo.
- Gemini / Pollinations ke free limits aur rules badalte rehte hain. Kuch band ho to Telegram alert aayega; tab `config.json` me `gemini_models` ke naam update kar do.
- GitHub Release links public hote hain (14 din baad apne aap delete). Kisi ko link mile to video download kar sakta hai; rhymes ke liye theek hai.
- Free tier me Gemini aapka input Google ke products sudharne me use kar sakta hai; business ka private data prompts me mat daalo.

## Test karna (optional, apne computer par)
```
pip install -r requirements.txt   # + ffmpeg install hona chahiye
python main.py daily --dry         # bina internet/keys ke nakli data se pura test
python -m unittest discover -s tests -v
```
