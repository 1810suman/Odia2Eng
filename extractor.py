# Requirements:
# pip install pytesseract pdf2image deep-translator
# You must have Tesseract-OCR and poppler installed and available on your machine.

import pytesseract
from pdf2image import convert_from_path
from deep_translator import GoogleTranslator
import re
import os

# === Configure these ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
poppler_path = '/usr/bin'

# ---------------------------------------------------------------------
# Helper class: transliteration + extraction + safe-translation
# ---------------------------------------------------------------------
class RoRDocumentExtractor:
    def __init__(self, source_lang="or", target_lang="en"):
        self.source_lang = source_lang
        self.target_lang = target_lang
        # Translator used only for translating non-proper-noun fields (safe fallback)
        try:
            self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
        except Exception:
            self.translator = None

        # Small Odia -> Latin phonetic maps (covers most common letters used in RoR docs)
        self.consonants = {
            "କ":"k","ଖ":"kh","ଗ":"g","ଘ":"gh","ଙ":"ng",
            "ଚ":"ch","ଛ":"chh","ଜ":"j","ଝ":"jh","ଞ":"ny",
            "ଟ":"t","ଠ":"th","ଡ":"d","ଢ":"dh","ଣ":"n",
            "ତ":"t","ଥ":"th","ଦ":"d","ଧ":"dh","ନ":"n",
            "ପ":"p","ଫ":"ph","ବ":"b","ଭ":"bh","ମ":"m",
            "ଯ":"y","ର":"r","ଲ":"l","ଶ":"sh","ଷ":"sh",
            "ସ":"s","ହ":"h","ଳ":"l",
        }
        self.independent_vowels = {
            "ଅ":"a","ଆ":"aa","ଇ":"i","ଈ":"ii","ଉ":"u","ଊ":"uu",
            "ଋ":"ru","ଏ":"e","ଐ":"ai","ଓ":"o","ଔ":"au",
        }
        self.vowel_signs = {
            "ା":"a","ି":"i","ୀ":"i","ୁ":"u","ୂ":"u","ୃ":"ru","େ":"e","ୈ":"ai","ୋ":"o","ୌ":"au",
        }
        self.diacritics = {
            "୍":"_virama",  # special-handled
            "ଂ":"n", "ଃ":"h"
        }
        # Precompiled odia-range test
        self._odia_re = re.compile(r"[\u0B00-\u0B7F]")

    # ---------------- OCR ----------------
    def extract_text(self, file_path, poppler_path=None, dpi=300):
        """Extract text from PDF (multi-page) or an image file."""
        print("Extracting text...")
        try:
            if file_path.lower().endswith(".pdf"):
                pages = convert_from_path(file_path, dpi, poppler_path=poppler_path)
                odia_text = ""
                for i, page in enumerate(pages):
                    text = pytesseract.image_to_string(page, lang=self.source_lang)
                    odia_text += text + "\n"
                    print(f"✅ Extracted text from page {i+1}")
            else:
                odia_text = pytesseract.image_to_string(file_path, lang=self.source_lang)
                print("✅ Extracted text from image.")
            # Debug: print first chunk so you can inspect OCR output
            print("--------- OCR OUTPUT START ---------")
            print(odia_text[:2000])
            print("--------- OCR OUTPUT END ---------")
            return odia_text
        except Exception as e:
            print("Error extracting text:", e)
            return ""

    # ---------------- Transliteration ----------------
    def odia_to_latin(self, text):
        """Naive phonetic transliteration of Odia -> Latin for proper nouns.
           This is intentionally conservative (keeps things readable)."""
        if not text or not self._odia_re.search(text):
            return text  # if no Odia letters, return as-is

        out = []
        s = text.strip()
        i = 0
        L = len(s)

        while i < L:
            ch = s[i]
            # independent vowel
            if ch in self.independent_vowels:
                out.append(self.independent_vowels[ch])
                i += 1
                continue
            # consonant
            if ch in self.consonants:
                base = self.consonants[ch]
                # lookahead for virama or vowel sign
                nxt = s[i+1] if i+1 < L else ""
                # virama (halant) => no inherent vowel
                if nxt == "୍":
                    out.append(base)
                    i += 2
                    continue
                # vowel sign attached
                if nxt in self.vowel_signs:
                    vs = self.vowel_signs[nxt]
                    out.append(base + vs)
                    i += 2
                    continue
                # default inherent 'a'
                out.append(base + "a")
                i += 1
                continue
            # vowel signs or diacritics alone
            if ch in self.vowel_signs:
                out.append(self.vowel_signs[ch])
                i += 1
                continue
            if ch in self.diacritics:
                # e.g. anusvara -> n
                val = self.diacritics[ch]
                if val != "_virama":
                    out.append(val)
                i += 1
                continue
            # whitespace / latin / punctuation
            out.append(ch)
            i += 1

        # cleanup spacing and repeated characters
        translit = "".join(out)
        translit = re.sub(r"\s+", " ", translit).strip()
        # Basic normalizations (double letters to single where appropriate)
        translit = translit.replace("ii", "i").replace("uu", "u")
        # Capitalize words
        translit = " ".join([w.capitalize() for w in translit.split()])
        return translit

    # ---------------- Safe translate (non-proper fields) ----------------
    def translate_field(self, text):
        if not text or text == "Not Found":
            return text
        if self.translator is None:
            return text
        try:
            return self.translator.translate(text.strip())
        except Exception as e:
            # fallback: return original Odia text (safer than wrong English)
            print("Translation error:", e)
            return text

    # ---------------- small helpers ----------------
    def find_value(self, patterns, text):
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE | re.DOTALL)
            if m:
                # return first non-empty capturing group or group(1)
                for g in m.groups():
                    if g:
                        return g.strip()
                return m.group(0).strip()
        return "Not Found"

    def get_value_from_lines(self, keyword, lines):
        for line in lines:
            if keyword in line:
                # try colon separated value
                parts = line.split(":")
                if len(parts) > 1:
                    # return remainder (strip numbers/punctuation)
                    val = parts[1].strip()
                    return val.split()[0] if val else "Not Found"
                # else remove the keyword and return first token
                val = line.replace(keyword, "").strip()
                return val.split()[0] if val else "Not Found"
        return "Not Found"

    # ---------------- Owner extraction (robust) ----------------
    def extract_owner_names_block(self, full_text, lines):
        """
        Look for owner list using a start marker (e.g. 'ପ୍ରଜାର ନାମ' or 'ଜମିଦାରଙ୍କ ନାମ')
        then take the text until the next stop keyword.
        """
        start_patterns = [
            r"(?:\d+\)\s*)?ପ୍ରଜାର\s*ନାମ",
            r"ଜମିଦାରଙ୍କ\s*ନାମ",
            r"ପ୍ରଜାର ନାମ[,:\s]*"  # fallback
        ]
        start_idx = None
        for sp in start_patterns:
            m = re.search(sp, full_text, re.IGNORECASE)
            if m:
                start_idx = m.end()
                break

        if start_idx is None:
            # try to find a line that looks like owner names (contains many Odia words and commas)
            for i, line in enumerate(lines):
                if line.count(",") >= 1 and self._odia_re.search(line):
                    return line  # heuristic fallback

            return ""

        # stop keywords that usually mark the end of the owner block
        stop_keywords = [
            "ସ୍ଵତ୍ତ୍", "ସ୍ଵତ୍ଵ", "ଖଜଣା", "ସେସ୍", "ନିସ୍ତାର", "ଡ଼ାଖଲ", "2)", "3)", "4)", "5)",
            "ଖତିୟାନ", "ପ୍ଲଟ", "କ୍ରମିକ", "କିସମ", "ଅନ୍ୟାନ୍ୟ", "ଅନ୍ତିମ", "ରାଷ୍ଟ୍ରୀୟ"
        ]
        end_idx = len(full_text)
        for kw in stop_keywords:
            k = full_text.find(kw, start_idx)
            if k != -1 and k < end_idx:
                end_idx = k

        names_block = full_text[start_idx:end_idx].strip()
        # Cleanup common tokens like "ପି:" (means "son of"): replace with comma so splitting keeps owner names
        names_block = re.sub(r"ପି[:\.\-]?", ",", names_block)
        # Remove stray ascii digits and punctuation that appear in OCR
        names_block = re.sub(r"[0-9\[\]\(\)\-:]+", " ", names_block)
        return names_block.strip()

    # ---------------- Main extraction ----------------
    def extract_info(self, odia_text):
        lines = [l.strip() for l in odia_text.splitlines() if l.strip()]
        full_text = " ".join(lines)

        # Try the most common simple patterns first, otherwise fallback to line search
        village_odia = self.find_value([r"ମୌଜା\s*[:\-]?\s*([^\n,:]+)"], full_text)
        if village_odia == "Not Found":
            village_odia = self.get_value_from_lines("ମୌଜା", lines)

        district_odia = self.find_value([r"ଜିଲ୍ଲା\s*[:\-]?\s*([^\n,:]+)"], full_text)
        if district_odia == "Not Found":
            district_odia = self.get_value_from_lines("ଜିଲ୍ଲା", lines)

        thana_odia = self.find_value([r"ଥାନା\s*[:\-]?\s*([^\n,:]+)"], full_text)
        if thana_odia == "Not Found":
            thana_odia = self.get_value_from_lines("ଥାନା", lines)

        # extract numbers (various spellings)
        thana_no = self.find_value([r"ଥାନା\s*ନ(?:ମ|ମ୍)ବର\s*[:\-]?\s*([0-9]+)",
                                    r"ଥାନା\s*[:\-]?.*?ନ(?:ମ|ମ୍)ବର\s*[:\-]?\s*([0-9]+)"], full_text)
        if thana_no == "Not Found":
            # line fallback
            for l in lines:
                if "ଥାନା" in l and re.search(r"[0-9]{2,}", l):
                    m = re.search(r"([0-9]{1,5})", l)
                    if m:
                        thana_no = m.group(1)
                        break

        tehsil_odia = self.find_value([r"ତହସିଲ\s*[:\-]?\s*([^\n,:]+)"], full_text)
        if tehsil_odia == "Not Found":
            tehsil_odia = self.get_value_from_lines("ତହସିଲ", lines)

        tehsil_no = self.find_value([r"ତହସିଲ\s*ନ(?:ମ|ମ୍)ବର\s*[:\-]?\s*([0-9]+)"], full_text)

        khata_no = self.find_value([r"ଖତିୟାନ(?:.*?କ୍ରମିକ)?\s*ନ(?:ମ|ମ୍)ବର\s*[:\-]?\s*([0-9]+)",
                                    r"ଖତିୟାନର\s*କ୍ରମିକ\s*ନ(?:ମ|ମ୍)ବର\s*[:\-]?\s*([0-9]+)"], full_text)

        plot_no = self.find_value([r"ପ୍ଲଟ\s*ନ(?:ମ|ମ୍)ବର\s*[:\-]?\s*([0-9]+)", r"ପ୍ଲଟ\s*[:\-]?\s*([0-9]+)"], full_text)

        land_type = self.find_value([r"କିସମ\s*[:\-]?\s*([^\n,]+)", r"କିସମ\s*ଓ\s*([^\n,]+)", r"(ପଦର[^\n,]+)"], full_text)
        if land_type == "Not Found":
            # sometimes Kisam is in a table separated by lines; try to find common words like 'ପଦର', 'ଦୁଇ'
            m = re.search(r"(ପଦର[^\d,\.]+)", full_text)
            if m:
                land_type = m.group(1).strip()

        # area (look for decimal)
        area_odia = self.find_value([r"([0-9]+\.[0-9]+)\s*(?:ହେକ୍ଟର|ହେକ୍ଟର)?", r"([0-9]+\.[0-9]+)"], full_text)

        # Owner names
        names_block = self.extract_owner_names_block(full_text, lines)
        owner_names_odia = []
        if names_block:
            # Split by commas/newlines/semicolons
            parts = [p.strip() for p in re.split(r"[,\n;]+", names_block) if p.strip()]
            # keep only parts containing Odia letters (filter out headings or stray words)
            owner_names_odia = [p for p in parts if self._odia_re.search(p)]

        # Build result: for proper-noun fields use transliteration, for "land-type" allow translation
        result = {}
        result["Village Name (Odia)"] = village_odia
        result["Village Name (Latin)"] = self.odia_to_latin(village_odia) if village_odia != "Not Found" else "Not Found"

        result["District (Odia)"] = district_odia
        result["District (Latin)"] = self.odia_to_latin(district_odia) if district_odia != "Not Found" else "Not Found"

        result["Police Station (Thana) (Odia)"] = thana_odia
        result["Police Station (Thana) (Latin)"] = self.odia_to_latin(thana_odia) if thana_odia != "Not Found" else "Not Found"

        result["Police Station No."] = thana_no
        result["Tehsil (Odia)"] = tehsil_odia
        result["Tehsil (Latin)"] = self.odia_to_latin(tehsil_odia) if tehsil_odia != "Not Found" else "Not Found"
        result["Tehsil No."] = tehsil_no

        result["Khata No."] = khata_no
        result["Plot No."] = plot_no

        result["Land Type (Odia)"] = land_type
        # Try to translate land_type (but fallback to showing transliteration)
        if land_type != "Not Found":
            translated_lt = self.translate_field(land_type)
            result["Land Type (English)"] = translated_lt if translated_lt else self.odia_to_latin(land_type)
        else:
            result["Land Type (English)"] = "Not Found"

        result["Area (hectares)"] = area_odia if area_odia != "Not Found" else "Not Found"

        result["Owner Names (Odia)"] = ", ".join(owner_names_odia) if owner_names_odia else "Not Found"
        # transliterate each owner name to Latin
        result["Owner Names (Latin)"] = ", ".join([self.odia_to_latin(n) for n in owner_names_odia]) if owner_names_odia else "Not Found"

        return result

    def format_output(self, extracted_info):
        out = "\n📑 Document Translation & Extracted Information\n\n"
        for k, v in extracted_info.items():
            out += f"- {k}: {v}\n"
        return out

# ---------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------
def extract_ror_info(pdf_path, poppler_path=None):
    extractor = RoRDocumentExtractor()
    odia_text = extractor.extract_text(pdf_path, poppler_path=poppler_path)
    if not odia_text:
        return "❌ Could not extract text. Check file path and dependencies."
    info = extractor.extract_info(odia_text)
    return extractor.format_output(info)

# ---------------------------------------------------------------------
# Example run (change paths before running)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    pdf_path = r"File_name"   # <-- change to your file
    poppler_path = r"\usr\bin" # <-- change to your poppler path or None
    print(extract_ror_info(pdf_path, poppler_path=poppler_path))

